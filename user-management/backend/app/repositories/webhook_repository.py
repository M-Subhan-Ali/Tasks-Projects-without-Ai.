"""Database access for webhook subscriptions and their delivery attempts."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WebhookDelivery, WebhookSubscription


def add_subscription(db: Session, subscription: WebhookSubscription) -> WebhookSubscription:
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def list_subscriptions(db: Session) -> list[WebhookSubscription]:
    return list(db.scalars(select(WebhookSubscription).order_by(WebhookSubscription.id)))


def get_subscription(db: Session, subscription_id: int) -> WebhookSubscription | None:
    return db.get(WebhookSubscription, subscription_id)


def list_subscriptions_for_event(db: Session, event: str) -> list[WebhookSubscription]:
    # `events` is a JSON list, which SQLite can't filter on portably, so the
    # filter runs in Python. Fine for the handful of subscriptions an app has.
    return [sub for sub in list_subscriptions(db) if event in sub.events]


def delete_subscription(db: Session, subscription: WebhookSubscription) -> None:
    db.delete(subscription)  # the relationship cascade deletes its deliveries too
    db.commit()


def add_delivery(db: Session, delivery: WebhookDelivery) -> WebhookDelivery:
    db.add(delivery)
    db.commit()
    return delivery


def list_deliveries(db: Session, subscription_id: int, limit: int) -> list[WebhookDelivery]:
    """Newest attempt first."""
    query = (
        select(WebhookDelivery)
        .where(WebhookDelivery.subscription_id == subscription_id)
        .order_by(WebhookDelivery.id.desc())
        .limit(limit)
    )
    return list(db.scalars(query))
