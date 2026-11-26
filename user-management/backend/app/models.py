from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(StrEnum):
    ADMIN = "admin"
    VIEWER = "viewer"


class WebhookEvent(StrEnum):
    """The events a webhook subscription can ask for."""

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"


# Emails must be unique among ACTIVE users only. A partial unique index covers
# just the rows that match its WHERE clause, so soft-deleted rows
# (is_deleted = 1) are skipped and their email can be used again.
# SQLite stores booleans as 0/1.
ACTIVE_USER_EMAIL_INDEX = "uq_users_email_active"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            ACTIVE_USER_EMAIL_INDEX,
            "email",
            unique=True,
            sqlite_where=text("is_deleted = 0"),
            postgresql_where=text("is_deleted = false"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # Not unique=True: that would also block the emails of deleted users.
    email: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(50))
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_name: Mapped[str] = mapped_column(String(100))
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class Account(Base):
    """A login account. Separate from User: a User is data the app manages,
    an Account is someone who can sign in and manage it."""

    __tablename__ = "accounts"
    __table_args__ = (
        # The database itself rejects any role other than admin/viewer,
        # even if a bug or a manual INSERT bypasses the Python code.
        CheckConstraint(
            "role IN ('admin', 'viewer')",
            name="ck_accounts_role",
        ),
        UniqueConstraint("email", name="uq_accounts_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100))
    # Never the password itself: an Argon2 hash (~100 characters).
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        String(20), default=Role.VIEWER.value, server_default=Role.VIEWER.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WebhookSubscription(Base):
    """An external URL that wants to be told when users change."""

    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048))
    # A list of WebhookEvent values, e.g. ["user.created", "user.deleted"].
    events: Mapped[list[str]] = mapped_column(JSON)
    # Stored as plain text on purpose: unlike a password, the server must be able
    # to READ it to sign every request. It is returned once, at registration.
    secret: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Deleting a subscription deletes its delivery history too. The ORM does it
    # (SQLite does not enforce foreign keys unless asked to).
    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class WebhookDelivery(Base):
    """One attempt to POST one event to one subscription. Retries are new rows."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey(
            "webhook_subscriptions.id",
            ondelete="CASCADE",
            name="fk_webhook_deliveries_subscription_id",
        ),
        index=True,
    )
    # Same for every attempt of one event, so retries can be grouped together.
    event_id: Mapped[str] = mapped_column(String(36))
    event: Mapped[str] = mapped_column(String(50))
    attempt: Mapped[int]
    success: Mapped[bool] = mapped_column(Boolean)
    # None when no response came back at all (timeout, connection refused).
    status_code: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(String(500))
    duration_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    subscription: Mapped[WebhookSubscription] = relationship(back_populates="deliveries")
