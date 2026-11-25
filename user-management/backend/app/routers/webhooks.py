"""HTTP layer for /webhooks: manage subscriptions and read their delivery history.

Admin only: a webhook sends user data to an outside URL, so only admins may
decide where it goes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Role
from app.schemas import WebhookCreate, WebhookCreatedResponse, WebhookDeliveryResponse, WebhookResponse
from app.services import webhook_service

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
    dependencies=[Depends(require_role(Role.ADMIN))],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=WebhookCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(data: WebhookCreate, db: DbSession) -> WebhookCreatedResponse:
    """The response includes the signing secret. It is shown only this once: save it."""
    subscription = webhook_service.create_subscription(db, data)
    return WebhookCreatedResponse.model_validate(subscription)


@router.get("", response_model=list[WebhookResponse])
def list_webhooks(db: DbSession) -> list[WebhookResponse]:
    # response_model=WebhookResponse has no `secret` field, so FastAPI drops it
    # even though the database row has one.
    return [WebhookResponse.model_validate(sub) for sub in webhook_service.list_subscriptions(db)]


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(webhook_id: int, db: DbSession) -> Response:
    webhook_service.delete_subscription(db, webhook_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
def list_webhook_deliveries(webhook_id: int, db: DbSession) -> list[WebhookDeliveryResponse]:
    """Every delivery attempt for this webhook, newest first (last 100)."""
    return [
        WebhookDeliveryResponse.model_validate(delivery)
        for delivery in webhook_service.list_deliveries(db, webhook_id)
    ]
