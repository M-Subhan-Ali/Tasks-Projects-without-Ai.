"""SSRF protection for webhooks: app/url_safety.py and app/safe_http.py.

Three layers are tested:
- registration (POST /webhooks): IP literals, localhost, and hostnames that
  resolve to internal addresses are refused with 422;
- delivery: every connection is checked again, so DNS that changes after
  registration (DNS rebinding) and webhooks saved before this check existed
  are blocked too;
- the guarded connection layer itself: it connects to the IP it checked.

DNS is faked by the `fake_dns` fixture (conftest.py) and no socket is ever
opened: a blocked destination is refused before connecting.
"""

import ipaddress
from typing import Any

import httpcore2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import config, safe_http, url_safety
from app.models import WebhookSubscription
from app.services import webhook_delivery
from tests.factories import PUBLIC_IP, user_payload

PRIVATE_URLS = [
    "http://10.0.0.1/hook",
    "http://10.255.255.254/hook",
    "http://172.16.0.1/hook",
    "http://172.31.255.254/hook",
    "http://192.168.1.10/hook",
    "http://[fc00::1]/hook",  # IPv6 unique local, the IPv6 "private" range
    "http://[::ffff:192.168.1.10]/hook",  # IPv4-mapped IPv6 = 192.168.1.10
]
LOOPBACK_URLS = [
    "http://127.0.0.1:8000/hook",
    "http://127.1.2.3/hook",  # all of 127.0.0.0/8, not just 127.0.0.1
    "http://[::1]/hook",
    "http://[::ffff:127.0.0.1]/hook",  # IPv4-mapped IPv6 = 127.0.0.1
    "http://2130706433/hook",  # 127.0.0.1 written as one number
]
LINK_LOCAL_URLS = [
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata service
    "http://169.254.0.1/hook",
    "http://[fe80::1]/hook",
]
LOCALHOST_URLS = [
    "http://localhost:9000/webhooks",
    "http://LOCALHOST:9000/webhooks",
    "http://api.localhost/hook",  # every *.localhost name is this machine
]


@pytest.fixture
def allow_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """ALLOW_LOCAL_WEBHOOKS=true, as on a developer's machine."""
    monkeypatch.setattr(config, "ALLOW_LOCAL_WEBHOOKS", True)


@pytest.fixture
def no_retry_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhook_delivery, "RETRY_DELAYS_SECONDS", (0, 0, 0))


def register(admin_client: TestClient, url: str) -> Any:
    return admin_client.post("/webhooks", json={"url": url, "events": ["user.created"]})


def url_error(response: Any) -> str:
    """The 422 message for the url field."""
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["detail"] == "Validation failed"
    [error] = body["errors"]
    assert error["field"] == "url"
    return error["message"]


# --- The required cases -----------------------------------------------------------


@pytest.mark.parametrize("url", PRIVATE_URLS)
def test_private_ip_is_rejected(admin_client: TestClient, url: str) -> None:
    assert "private address" in url_error(register(admin_client, url))


@pytest.mark.parametrize("url", LOOPBACK_URLS)
def test_loopback_ip_is_rejected(admin_client: TestClient, url: str) -> None:
    assert "loopback address" in url_error(register(admin_client, url))


@pytest.mark.parametrize("url", LINK_LOCAL_URLS)
def test_link_local_ip_is_rejected(admin_client: TestClient, url: str) -> None:
    assert "link-local address" in url_error(register(admin_client, url))


@pytest.mark.parametrize(
    "url",
    [
        f"https://{PUBLIC_IP}/hook",
        "https://receiver.test/webhooks",  # a hostname that resolves to a public IP
        "http://[2606:4700:4700::1111]/hook",  # a public IPv6 address
    ],
)
def test_public_url_is_accepted(admin_client: TestClient, url: str) -> None:
    response = register(admin_client, url)
    assert response.status_code == 201, response.text


@pytest.mark.parametrize("url", LOCALHOST_URLS)
def test_localhost_is_rejected_when_flag_false(admin_client: TestClient, url: str) -> None:
    assert config.ALLOW_LOCAL_WEBHOOKS is False  # the default
    assert "ALLOW_LOCAL_WEBHOOKS" in url_error(register(admin_client, url))


@pytest.mark.parametrize(
    "url", ["http://localhost:9000/webhooks", "http://127.0.0.1:9000/webhooks", "http://[::1]:9000/webhooks"]
)
def test_localhost_is_accepted_when_flag_true(admin_client: TestClient, allow_local: None, url: str) -> None:
    response = register(admin_client, url)
    assert response.status_code == 201, response.text


@pytest.mark.parametrize("url", PRIVATE_URLS + LINK_LOCAL_URLS)
def test_private_and_link_local_stay_blocked_when_flag_true(
    admin_client: TestClient, allow_local: None, url: str
) -> None:
    url_error(register(admin_client, url))


# --- Other addresses that aren't the public internet -------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://0.0.0.0/hook",  # "this host": connecting to it reaches localhost
        "http://100.64.0.1/hook",  # carrier-grade NAT, shared internal space
        "http://224.0.0.1/hook",  # multicast
        "http://255.255.255.255/hook",  # broadcast
        "http://[64:ff9b::a00:1]/hook",  # NAT64 address of 10.0.0.1
    ],
)
def test_other_non_public_addresses_are_rejected(admin_client: TestClient, url: str) -> None:
    url_error(register(admin_client, url))


# --- Hostnames: resolved and checked at registration --------------------------------


def test_hostname_resolving_to_private_ip_is_rejected(
    admin_client: TestClient, fake_dns: dict[str, list[str]]
) -> None:
    fake_dns["internal.test"] = ["10.0.0.5"]
    assert "10.0.0.5 is a private address" in url_error(register(admin_client, "https://internal.test/hook"))


def test_hostname_with_any_private_record_is_rejected(
    admin_client: TestClient, fake_dns: dict[str, list[str]]
) -> None:
    # One good record is not enough: the client could connect to the other one.
    fake_dns["mixed.test"] = [PUBLIC_IP, "192.168.0.2"]
    assert "192.168.0.2" in url_error(register(admin_client, "https://mixed.test/hook"))


def test_hostname_resolving_to_loopback_is_rejected(
    admin_client: TestClient, fake_dns: dict[str, list[str]]
) -> None:
    fake_dns["sneaky.test"] = ["127.0.0.1"]  # e.g. a public name pointed at 127.0.0.1
    assert "loopback" in url_error(register(admin_client, "http://sneaky.test/hook"))


def test_unresolvable_hostname_is_rejected(admin_client: TestClient) -> None:
    assert "could not resolve" in url_error(register(admin_client, "https://nowhere.test/hook"))


def test_rejected_webhooks_are_not_saved(admin_client: TestClient) -> None:
    for url in PRIVATE_URLS[:1] + LOOPBACK_URLS[:1] + LINK_LOCAL_URLS[:1] + ["https://nowhere.test/"]:
        register(admin_client, url)
    assert admin_client.get("/webhooks").json() == []


# --- Delivery: checked again on every connection -------------------------------------


def deliveries(admin_client: TestClient, webhook_id: int) -> list[dict[str, Any]]:
    response = admin_client.get(f"/webhooks/{webhook_id}/deliveries")
    assert response.status_code == 200, response.text
    return response.json()


def test_dns_rebinding_is_blocked_at_delivery(
    admin_client: TestClient, fake_dns: dict[str, list[str]], no_retry_waits: None
) -> None:
    # Public when the webhook is registered...
    fake_dns["rebind.test"] = [PUBLIC_IP]
    hook = register(admin_client, "http://rebind.test/hook").json()
    # ...then the attacker points the name at an internal service.
    fake_dns["rebind.test"] = ["127.0.0.1"]

    # This uses the REAL HTTP client: only the guard stands between it and 127.0.0.1.
    assert admin_client.post("/users", json=user_payload()).status_code == 201

    [attempt] = deliveries(admin_client, hook["id"])  # one attempt: a block is not retried
    assert attempt["success"] is False
    assert attempt["status_code"] is None  # nothing was sent
    assert attempt["error"].startswith("Blocked: 127.0.0.1 is a loopback address")


def test_webhook_saved_before_this_check_is_blocked_at_delivery(
    admin_client: TestClient, db_session: Session, no_retry_waits: None
) -> None:
    # A row from before the SSRF checks existed (e.g. already in users.db).
    old = WebhookSubscription(url="http://192.168.1.10/hook", events=["user.created"], secret="whsec_old")
    db_session.add(old)
    db_session.commit()

    admin_client.post("/users", json=user_payload())

    [attempt] = deliveries(admin_client, old.id)
    assert attempt["error"] == "Blocked: 192.168.1.10 is a private address"


def test_localhost_webhook_is_blocked_at_delivery_once_the_flag_is_off(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch, no_retry_waits: None
) -> None:
    monkeypatch.setattr(config, "ALLOW_LOCAL_WEBHOOKS", True)
    hook = register(admin_client, "http://localhost:9000/webhooks").json()
    monkeypatch.setattr(config, "ALLOW_LOCAL_WEBHOOKS", False)  # e.g. deployed with the default

    admin_client.post("/users", json=user_payload())

    [attempt] = deliveries(admin_client, hook["id"])
    assert attempt["error"].startswith("Blocked: localhost is not allowed")


def test_http_client_ignores_proxy_settings_and_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    # Through a proxy, the guard would only see the proxy's address.
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.test:3128")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.test:3128")

    with webhook_delivery.create_http_client() as client:
        assert client.follow_redirects is False
        assert client.trust_env is False
        # The request reaches the guard (not a proxy), which refuses it.
        with pytest.raises(url_safety.UnsafeDestination):
            client.post("http://10.0.0.1/hook", content=b"{}")


# --- The guarded connection layer -------------------------------------------------------


class RecordingBackend(httpcore2.NetworkBackend):
    """Stands in for the real socket layer and records where it was asked to connect."""

    def __init__(self, fail_for: set[str] | None = None) -> None:
        self.hosts: list[str] = []
        self.fail_for = fail_for or set()

    def connect_tcp(self, host: str, port: int, *args: Any, **kwargs: Any) -> httpcore2.NetworkStream:
        self.hosts.append(host)
        if host in self.fail_for:
            raise httpcore2.ConnectError("connection refused")
        return httpcore2.MockStream([])


def test_guard_connects_to_the_checked_ip_not_the_hostname() -> None:
    inner = RecordingBackend()
    safe_http.GuardedBackend(allow_local=False, inner=inner).connect_tcp("receiver.test", 443)

    # The socket gets the IP that was checked, so DNS can't answer differently a second time.
    assert inner.hosts == [PUBLIC_IP]


def test_guard_refuses_before_opening_a_socket(fake_dns: dict[str, list[str]]) -> None:
    fake_dns["internal.test"] = ["10.0.0.5"]
    inner = RecordingBackend()

    with pytest.raises(url_safety.UnsafeDestination):
        safe_http.GuardedBackend(allow_local=False, inner=inner).connect_tcp("internal.test", 80)
    assert inner.hosts == []


def test_guard_tries_the_next_checked_address(fake_dns: dict[str, list[str]]) -> None:
    fake_dns["dual.test"] = ["2606:4700:4700::1111", PUBLIC_IP]
    inner = RecordingBackend(fail_for={"2606:4700:4700::1111"})  # no IPv6 here

    safe_http.GuardedBackend(allow_local=False, inner=inner).connect_tcp("dual.test", 443)

    assert inner.hosts == ["2606:4700:4700::1111", PUBLIC_IP]


def test_guarded_transport_uses_the_guard() -> None:
    # Fails if an httpx2 upgrade changes how the transport's pool is built.
    transport = safe_http.GuardedTransport(allow_local=False)
    assert isinstance(transport._pool, httpcore2.ConnectionPool)
    assert isinstance(transport._pool._network_backend, safe_http.GuardedBackend)


# --- check_ip: the required ranges, edge to edge ------------------------------------------


@pytest.mark.parametrize(
    ("address", "reason"),
    [
        ("127.0.0.0", "loopback"),
        ("127.255.255.255", "loopback"),
        ("10.0.0.0", "private"),
        ("10.255.255.255", "private"),
        ("172.16.0.0", "private"),
        ("172.31.255.255", "private"),
        ("192.168.0.0", "private"),
        ("192.168.255.255", "private"),
        ("169.254.0.0", "link-local"),
        ("169.254.255.255", "link-local"),
        ("::1", "loopback"),
        ("fe80::1", "link-local"),
    ],
)
def test_required_ranges_are_blocked(address: str, reason: str) -> None:
    with pytest.raises(url_safety.UnsafeDestination, match=reason):
        url_safety.check_ip(ipaddress.ip_address(address), allow_local=False)


@pytest.mark.parametrize("address", ["9.255.255.255", "11.0.0.0", "172.15.255.255", "172.32.0.0", "192.167.255.255", "192.169.0.0"])
def test_addresses_just_outside_the_ranges_are_allowed(address: str) -> None:
    url_safety.check_ip(ipaddress.ip_address(address), allow_local=False)  # does not raise


def test_flag_allows_loopback_only() -> None:
    url_safety.check_ip(ipaddress.ip_address("127.0.0.1"), allow_local=True)
    url_safety.check_ip(ipaddress.ip_address("::1"), allow_local=True)
    for address in ["10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.169.254", "fe80::1"]:
        with pytest.raises(url_safety.UnsafeDestination):
            url_safety.check_ip(ipaddress.ip_address(address), allow_local=True)
