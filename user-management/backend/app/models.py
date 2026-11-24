from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    String,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Role(StrEnum):
    ADMIN = "admin"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
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
