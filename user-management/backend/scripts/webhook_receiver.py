"""A small, separate app that RECEIVES webhooks from the User Management API.

It plays the part of an external system. It imports nothing from app/ on
purpose: a real receiver only knows the shared secret and the signing rules.

Run it (port 9000), with the secret from the POST /webhooks response:

    $env:WEBHOOK_SECRET = "whsec_..."
    python -m scripts.webhook_receiver

Then register http://localhost:9000/webhooks as the webhook URL.

For every request it:
1. checks X-Webhook-Timestamp is a number and at most 5 minutes old (or ahead),
   so a captured request can't be replayed later;
2. recomputes HMAC-SHA256(secret, "<timestamp>.<raw body>") and compares it with
   X-Webhook-Signature in constant time, so a forged or altered request is refused;
3. logs the event, and ignores an event_id it has already processed (a retry
   can deliver the same event twice).
"""

import hashlib
import hmac
import json
import logging
import os
import time
from collections import OrderedDict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

PORT = 9000
SIGNATURE_HEADER = "X-Webhook-Signature"
TIMESTAMP_HEADER = "X-Webhook-Timestamp"
TOLERANCE_SECONDS = 300
MAX_REMEMBERED_EVENTS = 1000

logger = logging.getLogger("webhook_receiver")

app = FastAPI(title="Webhook Receiver")

# event_ids already processed, oldest first (bounded so memory can't grow forever).
_seen_event_ids: OrderedDict[str, None] = OrderedDict()


def get_secret() -> str:
    # Read on every request, so tests (and you) can change it without a restart.
    return os.environ.get("WEBHOOK_SECRET", "")


def is_timestamp_fresh(timestamp: str, now: float) -> bool:
    if not timestamp.isdigit():
        return False
    return abs(now - int(timestamp)) <= TOLERANCE_SECONDS


def expected_signature(secret: str, timestamp: str, body: bytes) -> str:
    message = timestamp.encode() + b"." + body
    return "sha256=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def is_signature_valid(secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    # compare_digest takes the same time however many characters match, so an
    # attacker can't guess the signature one character at a time.
    return hmac.compare_digest(expected_signature(secret, timestamp, body), signature)


def _remember(event_id: str) -> bool:
    """Return False if this event_id was already processed."""
    if event_id in _seen_event_ids:
        return False
    _seen_event_ids[event_id] = None
    if len(_seen_event_ids) > MAX_REMEMBERED_EVENTS:
        _seen_event_ids.popitem(last=False)
    return True


def _reject(status_code: int, reason: str) -> JSONResponse:
    logger.warning("Rejected webhook: %s", reason)
    return JSONResponse(status_code=status_code, content={"detail": reason})


@app.post("/webhooks")
async def receive_webhook(request: Request) -> JSONResponse:
    secret = get_secret()
    if not secret:
        return _reject(500, "WEBHOOK_SECRET is not set on the receiver")

    timestamp = request.headers.get(TIMESTAMP_HEADER, "")
    signature = request.headers.get(SIGNATURE_HEADER, "")
    # The RAW bytes: re-encoding parsed JSON could change spacing and break the HMAC.
    body = await request.body()

    if not is_timestamp_fresh(timestamp, time.time()):
        return _reject(400, "Missing, invalid or expired timestamp")
    if not is_signature_valid(secret, timestamp, body, signature):
        return _reject(401, "Invalid signature")

    event = json.loads(body)
    if not _remember(event["event_id"]):
        logger.info("Duplicate event ignored event_id=%s", event["event_id"])
        return JSONResponse({"received": True, "duplicate": True})

    user = event["data"]
    logger.info(
        "Received %s at %s: user id=%s name=%r",
        event["event"], event["timestamp"], user["id"], user["name"],
    )
    return JSONResponse({"received": True})


if __name__ == "__main__":
    # Configured here, not at import, so importing this module (in tests) doesn't
    # change the logging setup of whoever imports it.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [receiver] %(message)s",
        datefmt="%H:%M:%S",
    )
    if not get_secret():
        raise SystemExit(
            "Set WEBHOOK_SECRET first (the secret from the POST /webhooks response):\n"
            '  $env:WEBHOOK_SECRET = "whsec_..."'
        )
    logger.info("Listening on http://localhost:%d/webhooks", PORT)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
