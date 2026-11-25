"""Logging tests: every log line is traceable to its request, and secrets never leak.

caplog is pytest's built-in fixture that captures log records during a test.
"""

import logging
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

EMAIL = "log.check@example.com"
PASSWORD = "a password that must never be logged"
# Must not look like any log message text ("wrong password" would match
# "Login failed: wrong password" and fail the test for the wrong reason).
WRONG_PASSWORD = "Xq7-typo-in-the-password"


def test_service_log_lines_carry_the_request_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    request_id = str(uuid.uuid4())

    response = client.post(
        "/auth/register",
        json={"email": EMAIL, "password": PASSWORD},
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 201
    service_records = [r for r in caplog.records if r.name == "app.services.auth_service"]
    request_records = [r for r in caplog.records if r.name == "app.requests"]
    assert service_records and request_records
    # The service line and the request line can be matched by their ID.
    assert {r.request_id for r in service_records + request_records} == {request_id}


def test_auth_logs_never_contain_password_or_email(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    credentials: dict[str, Any] = {"email": EMAIL, "password": PASSWORD}

    client.post("/auth/register", json=credentials)
    client.post("/auth/login", json={**credentials, "password": WRONG_PASSWORD})
    client.post("/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    client.post("/auth/login", json=credentials)

    assert "Login failed: wrong password" in caplog.text
    assert "Login failed: unknown email" in caplog.text
    assert "Login succeeded" in caplog.text
    for secret in (PASSWORD, WRONG_PASSWORD, EMAIL, "nobody@example.com", "$argon2"):
        assert secret not in caplog.text


def test_permission_denied_is_logged_as_warning(
    viewer_client: TestClient, create_user: Any, caplog: pytest.LogCaptureFixture
) -> None:
    user = create_user()
    caplog.set_level(logging.INFO)

    response = viewer_client.delete(f"/users/{user['id']}")

    assert response.status_code == 403
    assert any(
        r.levelno == logging.WARNING and r.getMessage().startswith("Permission denied")
        for r in caplog.records
    )


def test_log_lines_outside_a_request_show_a_dash() -> None:
    make_record = logging.getLogRecordFactory()

    record = make_record("startup", logging.INFO, __file__, 1, "message", None, None)

    assert record.request_id == "-"
