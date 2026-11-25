"""Webhook tests: registration, signed delivery, retries, history, and the receiver.

No real HTTP is sent. The `receiver` fixture swaps the delivery code's HTTP
client for one built on httpx2.MockTransport, which hands every request to a
Python function instead of the network. That function records the request and
answers with whatever status code (or network error) the test asks for.

FastAPI's TestClient runs background tasks before returning, so by the time
`admin_client.post("/users", ...)` returns, the webhook has been "delivered".
"""

import hashlib
import hmac
import json
import time
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WebhookDelivery, WebhookSubscription
from app.services import webhook_delivery
from scripts import webhook_receiver
from tests.factories import user_payload

RECEIVER_URL = "http://receiver.test/webhooks"
ALL_EVENTS = ["user.created", "user.updated", "user.deleted"]

# What the fake receiver answers: a status code, or a network error class to raise.
Reply = int | type[httpx2.HTTPError]


@dataclass
class FakeReceiver:
    replies: list[Reply] = field(default_factory=list)  # used in order, then 200
    requests: list[httpx2.Request] = field(default_factory=list)

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        reply = self.replies.pop(0) if self.replies else 200
        if isinstance(reply, int):
            return httpx2.Response(reply)
        raise reply("simulated network failure", request=request)

    def events(self) -> list[str]:
        return [json.loads(request.content)["event"] for request in self.requests]


@pytest.fixture
def receiver(monkeypatch: pytest.MonkeyPatch) -> FakeReceiver:
    fake = FakeReceiver()
    monkeypatch.setattr(
        webhook_delivery,
        "create_http_client",
        lambda: httpx2.Client(transport=httpx2.MockTransport(fake.handle)),
    )
    monkeypatch.setattr(webhook_delivery, "RETRY_DELAYS_SECONDS", (0, 0, 0))  # no waiting
    return fake


def register(admin_client: TestClient, events: list[str] = ALL_EVENTS) -> dict[str, Any]:
    response = admin_client.post("/webhooks", json={"url": RECEIVER_URL, "events": events})
    assert response.status_code == 201, response.text
    return response.json()


def get_deliveries(admin_client: TestClient, webhook_id: int) -> list[dict[str, Any]]:
    response = admin_client.get(f"/webhooks/{webhook_id}/deliveries")
    assert response.status_code == 200, response.text
    return response.json()


# --- Registration and the secret -----------------------------------------------


def test_register_returns_secret_only_once(admin_client: TestClient, db_session: Session) -> None:
    created = register(admin_client, ["user.created"])

    assert created["url"] == RECEIVER_URL
    assert created["events"] == ["user.created"]
    assert created["secret"].startswith("whsec_")
    assert len(created["secret"]) > 40

    # The list never shows it again...
    listed = admin_client.get("/webhooks").json()
    assert listed == [{key: value for key, value in created.items() if key != "secret"}]
    # ...but the server kept it, because it needs it to sign deliveries.
    stored = db_session.get(WebhookSubscription, created["id"])
    assert stored is not None and stored.secret == created["secret"]


def test_each_webhook_gets_its_own_secret(admin_client: TestClient) -> None:
    assert register(admin_client)["secret"] != register(admin_client)["secret"]


@pytest.mark.parametrize(
    "body",
    [
        {"url": "ftp://receiver.test/hook", "events": ["user.created"]},
        {"url": "not a url", "events": ["user.created"]},
        {"url": RECEIVER_URL, "events": []},
        {"url": RECEIVER_URL, "events": ["user.exploded"]},
    ],
)
def test_register_rejects_bad_url_or_events(admin_client: TestClient, body: dict[str, Any]) -> None:
    assert admin_client.post("/webhooks", json=body).status_code == 422


def test_viewer_cannot_manage_webhooks(viewer_client: TestClient) -> None:
    body = {"url": RECEIVER_URL, "events": ["user.created"]}
    assert viewer_client.post("/webhooks", json=body).status_code == 403
    assert viewer_client.get("/webhooks").status_code == 403


# --- Payload and signature -------------------------------------------------------


def test_user_created_sends_signed_payload(admin_client: TestClient, receiver: FakeReceiver) -> None:
    hook = register(admin_client, ["user.created"])
    sent_after = int(time.time())

    user = admin_client.post("/users", json=user_payload()).json()

    assert len(receiver.requests) == 1
    request = receiver.requests[0]
    assert request.method == "POST"
    assert str(request.url) == RECEIVER_URL
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["X-Webhook-Event"] == "user.created"

    payload = json.loads(request.content)
    assert payload["event"] == "user.created"
    assert payload["data"] == user  # exactly what the API returned
    assert payload["event_id"]
    assert datetime.fromisoformat(payload["timestamp"]).tzinfo is not None

    timestamp = request.headers["X-Webhook-Timestamp"]
    assert sent_after <= int(timestamp) <= time.time() + 1

    # Recompute the HMAC the way any receiver would, over the exact bytes sent.
    expected = hmac.new(
        hook["secret"].encode(), f"{timestamp}.".encode() + request.content, hashlib.sha256
    ).hexdigest()
    assert request.headers["X-Webhook-Signature"] == f"sha256={expected}"


def test_update_and_delete_send_their_events(
    admin_client: TestClient, receiver: FakeReceiver
) -> None:
    register(admin_client)
    user = admin_client.post("/users", json=user_payload()).json()

    admin_client.patch(f"/users/{user['id']}", json={"city": "Karachi"})
    admin_client.put(f"/users/{user['id']}", json=user_payload(name="Sara Khan"))
    admin_client.delete(f"/users/{user['id']}")

    assert receiver.events() == ["user.created", "user.updated", "user.updated", "user.deleted"]
    payloads = [json.loads(request.content) for request in receiver.requests]
    assert payloads[1]["data"]["city"] == "Karachi"
    assert payloads[2]["data"]["name"] == "Sara Khan"
    assert payloads[3]["data"]["id"] == user["id"]
    # Every event gets its own ID.
    assert len({payload["event_id"] for payload in payloads}) == 4


def test_only_subscribed_events_are_sent(admin_client: TestClient, receiver: FakeReceiver) -> None:
    register(admin_client, ["user.deleted"])
    user = admin_client.post("/users", json=user_payload()).json()
    admin_client.patch(f"/users/{user['id']}", json={"city": "Karachi"})
    assert receiver.requests == []

    admin_client.delete(f"/users/{user['id']}")
    assert receiver.events() == ["user.deleted"]


def test_http_client_uses_a_5_second_timeout() -> None:
    with webhook_delivery.create_http_client() as client:
        assert client.timeout.connect == 5.0
        assert client.timeout.read == 5.0


# --- Retries -----------------------------------------------------------------------


def test_failed_delivery_is_retried_3_times(admin_client: TestClient, receiver: FakeReceiver) -> None:
    receiver.replies = [500] * 10  # the receiver is broken for good
    hook = register(admin_client, ["user.created"])

    response = admin_client.post("/users", json=user_payload())

    assert response.status_code == 201  # a broken receiver never breaks the API
    assert len(receiver.requests) == 4  # 1 attempt + 3 retries, then it gives up
    deliveries = get_deliveries(admin_client, hook["id"])
    assert [d["attempt"] for d in deliveries] == [4, 3, 2, 1]  # newest first
    assert all(not d["success"] and d["status_code"] == 500 for d in deliveries)
    assert all(d["error"] == "HTTP 500" for d in deliveries)
    assert len({d["event_id"] for d in deliveries}) == 1  # all for the same event


def test_retry_stops_after_a_success(admin_client: TestClient, receiver: FakeReceiver) -> None:
    receiver.replies = [503, httpx2.ConnectError]  # then 200
    hook = register(admin_client, ["user.created"])

    admin_client.post("/users", json=user_payload())

    assert len(receiver.requests) == 3
    third, second, first = get_deliveries(admin_client, hook["id"])
    assert (first["status_code"], first["error"]) == (503, "HTTP 503")
    assert second["status_code"] is None  # no response at all
    assert second["error"].startswith("ConnectError")
    assert (third["attempt"], third["success"], third["status_code"]) == (3, True, 200)
    # Same body every time: a retry is the same event, re-signed.
    assert len({request.content for request in receiver.requests}) == 1


def test_timeout_counts_as_a_failed_attempt(admin_client: TestClient, receiver: FakeReceiver) -> None:
    receiver.replies = [httpx2.ReadTimeout]
    hook = register(admin_client, ["user.created"])

    admin_client.post("/users", json=user_payload())

    second, first = get_deliveries(admin_client, hook["id"])
    assert first["error"].startswith("ReadTimeout") and not first["success"]
    assert second["success"]


# --- No event when the change fails ----------------------------------------------


def test_no_webhook_when_user_change_fails(admin_client: TestClient, receiver: FakeReceiver) -> None:
    register(admin_client)

    assert admin_client.post("/users", json=user_payload(name="")).status_code == 422
    assert receiver.requests == []

    admin_client.post("/users", json=user_payload())  # the one success
    assert admin_client.post("/users", json=user_payload()).status_code == 409  # duplicate
    assert admin_client.patch("/users/9999", json={"city": "Karachi"}).status_code == 404
    assert admin_client.delete("/users/9999").status_code == 404

    assert receiver.events() == ["user.created"]


def test_no_webhook_when_viewer_is_refused(
    admin_client: TestClient, viewer_client: TestClient, receiver: FakeReceiver
) -> None:
    register(admin_client)
    assert viewer_client.post("/users", json=user_payload()).status_code == 403
    assert receiver.requests == []


# --- Delivery history ------------------------------------------------------------------


def test_delivery_attempts_are_saved_in_database(
    admin_client: TestClient, receiver: FakeReceiver, db_session: Session
) -> None:
    hook = register(admin_client, ["user.created"])
    admin_client.post("/users", json=user_payload())
    sent_event_id = json.loads(receiver.requests[0].content)["event_id"]

    rows = db_session.scalars(select(WebhookDelivery)).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.subscription_id == hook["id"]
    assert (row.event, row.event_id, row.attempt) == ("user.created", sent_event_id, 1)
    assert (row.success, row.status_code, row.error) == (True, 200, None)
    assert row.duration_ms >= 0

    [listed] = get_deliveries(admin_client, hook["id"])
    assert listed["id"] == row.id and listed["success"] is True


def test_deliveries_of_unknown_webhook_returns_404(admin_client: TestClient) -> None:
    assert admin_client.get("/webhooks/9999/deliveries").status_code == 404


def test_delete_webhook_removes_it_and_its_history(
    admin_client: TestClient, receiver: FakeReceiver, db_session: Session
) -> None:
    hook = register(admin_client, ["user.created"])
    admin_client.post("/users", json=user_payload())

    assert admin_client.delete(f"/webhooks/{hook['id']}").status_code == 204

    assert admin_client.get("/webhooks").json() == []
    assert admin_client.get(f"/webhooks/{hook['id']}/deliveries").status_code == 404
    assert db_session.scalars(select(WebhookDelivery)).all() == []
    assert admin_client.delete(f"/webhooks/{hook['id']}").status_code == 404

    admin_client.post("/users", json=user_payload(email="other@example.com"))
    assert len(receiver.requests) == 1  # nothing sent after the webhook was deleted


# --- The receiver app (scripts/webhook_receiver.py) -------------------------------------

RECEIVER_SECRET = "whsec_test-secret"


@pytest.fixture
def receiver_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("WEBHOOK_SECRET", RECEIVER_SECRET)
    monkeypatch.setattr(webhook_receiver, "_seen_event_ids", OrderedDict())
    with TestClient(webhook_receiver.app) as test_client:
        yield test_client


def signed_body(event_id: str = "evt-1") -> bytes:
    user = {"id": 1, "name": "Ali Raza", "email": "ali.raza@example.com"}
    payload = webhook_delivery.build_payload("user.created", user, event_id, datetime.now())
    return json.dumps(payload).encode()


def signed_headers(body: bytes, timestamp: int | None = None, secret: str = RECEIVER_SECRET) -> dict[str, str]:
    ts = str(int(time.time()) if timestamp is None else timestamp)
    # Signed with the API's own sign(): proves sender and receiver agree.
    return {
        "X-Webhook-Timestamp": ts,
        "X-Webhook-Signature": webhook_delivery.sign(secret, ts, body),
    }


def test_receiver_accepts_a_correctly_signed_event(receiver_client: TestClient) -> None:
    body = signed_body()

    first = receiver_client.post("/webhooks", content=body, headers=signed_headers(body))
    assert first.status_code == 200
    assert first.json() == {"received": True}

    # A retry of the same event is accepted but not processed twice.
    again = receiver_client.post("/webhooks", content=body, headers=signed_headers(body))
    assert again.json() == {"received": True, "duplicate": True}


def test_receiver_rejects_bad_signatures(receiver_client: TestClient) -> None:
    body = signed_body()
    tampered = body.replace(b"Ali Raza", b"Evil Name")

    assert receiver_client.post("/webhooks", content=tampered, headers=signed_headers(body)).status_code == 401
    wrong_secret = signed_headers(body, secret="whsec_someone-else")
    assert receiver_client.post("/webhooks", content=body, headers=wrong_secret).status_code == 401
    no_signature = {"X-Webhook-Timestamp": str(int(time.time()))}
    assert receiver_client.post("/webhooks", content=body, headers=no_signature).status_code == 401


@pytest.mark.parametrize("timestamp", [None, "not-a-number", "OLD", "FUTURE"])
def test_receiver_rejects_missing_or_stale_timestamp(
    receiver_client: TestClient, timestamp: str | None
) -> None:
    body = signed_body()
    now = int(time.time())
    if timestamp == "OLD":
        headers = signed_headers(body, timestamp=now - 301)  # validly signed, but too old
    elif timestamp == "FUTURE":
        headers = signed_headers(body, timestamp=now + 301)
    else:
        headers = signed_headers(body)
        if timestamp is None:
            del headers["X-Webhook-Timestamp"]
        else:
            headers["X-Webhook-Timestamp"] = timestamp

    assert receiver_client.post("/webhooks", content=body, headers=headers).status_code == 400
