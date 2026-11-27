"""Send webhook events: sign, POST, retry, and record every attempt.

Runs as a FastAPI background task, i.e. AFTER the API response has been sent,
so a slow or broken receiver never slows down the user's request.

What a receiver gets:

    POST <subscription url>
    Content-Type: application/json
    X-Webhook-Event: user.created
    X-Webhook-Timestamp: 1764079200                 (Unix seconds, when SENT)
    X-Webhook-Signature: sha256=<hex HMAC>

    {"event_id": "...", "event": "user.created",
     "timestamp": "2026-11-25T12:00:00+00:00",      (when the event HAPPENED)
     "data": {"id": 1, "name": ..., "email": ..., ...}}

Signature = HMAC-SHA256(key=secret, message="<X-Webhook-Timestamp>.<raw body>").
The timestamp is part of the signed message, so an attacker who captured a
request can't resend it later with a fresh timestamp: the signature would break.

SSRF: the HTTP client comes from safe_http, which checks the IP of every
connection it opens. A blocked destination is saved as a failed attempt
("Blocked: ...") and is not retried: the answer would be the same.
"""

import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx2
from sqlalchemy.orm import Session, sessionmaker

from app import config, safe_http, url_safety
from app.models import WebhookDelivery, WebhookSubscription
from app.repositories import webhook_repository

# Log IDs, events and status codes only: never the body (user data),
# the secret or the signature.
logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-Webhook-Signature"
TIMESTAMP_HEADER = "X-Webhook-Timestamp"
EVENT_HEADER = "X-Webhook-Event"

TIMEOUT_SECONDS = 5.0
MAX_RETRIES = 3  # 1 first attempt + up to 3 retries = at most 4 attempts
# Wait before retry 1, 2 and 3. Growing waits give a struggling receiver time
# to recover instead of hammering it. Tests set these to 0.
RETRY_DELAYS_SECONDS: tuple[float, ...] = (1, 2, 4)
MAX_ERROR_LENGTH = 500  # the size of webhook_deliveries.error
BLOCKED_PREFIX = "Blocked: "  # error text of an attempt refused by the SSRF guard


def sign(secret: str, timestamp: str, body: bytes) -> str:
    message = timestamp.encode() + b"." + body
    digest = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def build_payload(event: str, user: dict[str, Any], event_id: str, occurred_at: datetime) -> dict[str, Any]:
    return {
        "event_id": event_id,  # lets the receiver ignore a duplicate after a retry
        "event": event,
        "timestamp": occurred_at.isoformat(),
        "data": user,
    }


def create_http_client() -> httpx2.Client:
    # Checks the IP of every connection (SSRF) and never follows redirects, so
    # a receiver can't bounce our signed request to some other address.
    # config.ALLOW_LOCAL_WEBHOOKS is read on every delivery, not once at import.
    return safe_http.create_guarded_client(TIMEOUT_SECONDS, config.ALLOW_LOCAL_WEBHOOKS)


def deliver_event(session_factory: sessionmaker[Session], event: str, user: dict[str, Any]) -> None:
    """Background task: send one event to every subscription that asked for it."""
    event_id = str(uuid.uuid4())
    payload = build_payload(event, user, event_id, datetime.now(timezone.utc))
    # Serialise ONCE: the signature must be computed over exactly the bytes sent.
    body = json.dumps(payload, separators=(",", ":")).encode()

    with session_factory() as db:
        subscriptions = webhook_repository.list_subscriptions_for_event(db, event)
        if not subscriptions:
            return

        logger.info(
            "Delivering %s event_id=%s to %d webhook(s)", event, event_id, len(subscriptions)
        )
        with create_http_client() as client:
            for subscription in subscriptions:
                _deliver_with_retries(db, client, subscription, event, event_id, body)


def _deliver_with_retries(
    db: Session,
    client: httpx2.Client,
    subscription: WebhookSubscription,
    event: str,
    event_id: str,
    body: bytes,
) -> None:
    for attempt in range(1, MAX_RETRIES + 2):
        delivery = _attempt(client, subscription, event, event_id, body, attempt)
        webhook_repository.add_delivery(db, delivery)

        if delivery.success:
            logger.info(
                "Webhook delivered webhook_id=%s event=%s attempt=%d status=%s",
                subscription.id, event, attempt, delivery.status_code,
            )
            return

        logger.warning(
            "Webhook delivery failed webhook_id=%s event=%s attempt=%d error=%s",
            subscription.id, event, attempt, delivery.error,
        )
        if delivery.error is not None and delivery.error.startswith(BLOCKED_PREFIX):
            # Retrying can't help: the destination is not allowed.
            return
        if attempt <= MAX_RETRIES:
            time.sleep(RETRY_DELAYS_SECONDS[attempt - 1])

    logger.error(
        "Webhook gave up after %d attempts webhook_id=%s event=%s event_id=%s",
        MAX_RETRIES + 1, subscription.id, event, event_id,
    )


def _attempt(
    client: httpx2.Client,
    subscription: WebhookSubscription,
    event: str,
    event_id: str,
    body: bytes,
    attempt: int,
) -> WebhookDelivery:
    # A fresh timestamp (and so a fresh signature) per attempt: a retry sent
    # minutes later must still pass the receiver's "not too old" check.
    timestamp = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        EVENT_HEADER: event,
        TIMESTAMP_HEADER: timestamp,
        SIGNATURE_HEADER: sign(subscription.secret, timestamp, body),
    }

    status_code: int | None = None
    error: str | None = None
    started_at = time.perf_counter()
    try:
        response = client.post(subscription.url, content=body, headers=headers)
        status_code = response.status_code
        if not response.is_success:
            error = f"HTTP {status_code}"
    except url_safety.UnsafeDestination as exc:
        # Refused by safe_http before any connection was opened.
        error = f"{BLOCKED_PREFIX}{exc}"[:MAX_ERROR_LENGTH]
    except (httpx2.HTTPError, httpx2.InvalidURL) as exc:
        # Timeout, connection refused, DNS failure...: no response at all.
        error = f"{type(exc).__name__}: {exc}"[:MAX_ERROR_LENGTH]

    return WebhookDelivery(
        subscription_id=subscription.id,
        event_id=event_id,
        event=event,
        attempt=attempt,
        success=error is None,
        status_code=status_code,
        error=error,
        duration_ms=round((time.perf_counter() - started_at) * 1000),
    )
