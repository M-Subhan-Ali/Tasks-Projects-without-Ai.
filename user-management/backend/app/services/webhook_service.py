"""Business rules for managing webhook subscriptions (no HTTP, no FastAPI)."""

import logging
import secrets

from sqlalchemy.orm import Session

from app.exceptions import WebhookNotFound
from app.models import WebhookDelivery, WebhookSubscription
from app.repositories import webhook_repository
from app.schemas import WebhookCreate

# Never log the secret or the URL's query string (it may hold tokens).
logger = logging.getLogger(__name__)

SECRET_PREFIX = "whsec_"  # makes a leaked secret easy to recognise (and to scan for)
DELIVERY_HISTORY_LIMIT = 100


def generate_secret() -> str:
    # 32 random bytes from the OS's secure generator: impossible to guess.
    return SECRET_PREFIX + secrets.token_urlsafe(32)


def create_subscription(db: Session, data: WebhookCreate) -> WebhookSubscription:
    subscription = WebhookSubscription(
        url=str(data.url),
        events=[event.value for event in data.events],
        secret=generate_secret(),
    )
    subscription = webhook_repository.add_subscription(db, subscription)
    logger.info(
        "Webhook registered webhook_id=%s events=%s", subscription.id, subscription.events
    )
    return subscription


def list_subscriptions(db: Session) -> list[WebhookSubscription]:
    return webhook_repository.list_subscriptions(db)


def get_subscription(db: Session, subscription_id: int) -> WebhookSubscription:
    subscription = webhook_repository.get_subscription(db, subscription_id)
    if subscription is None:
        raise WebhookNotFound(subscription_id)
    return subscription


def delete_subscription(db: Session, subscription_id: int) -> None:
    subscription = get_subscription(db, subscription_id)
    webhook_repository.delete_subscription(db, subscription)
    logger.info("Webhook deleted webhook_id=%s", subscription_id)


def list_deliveries(db: Session, subscription_id: int) -> list[WebhookDelivery]:
    get_subscription(db, subscription_id)  # 404 if the webhook doesn't exist
    return webhook_repository.list_deliveries(db, subscription_id, DELIVERY_HISTORY_LIMIT)
