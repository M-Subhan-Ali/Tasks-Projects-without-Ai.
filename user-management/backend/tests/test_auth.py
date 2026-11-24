"""Security tests: registration, password storage, login, tokens and roles."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from app.models import Account, Role
from app.security import create_access_token
from tests.factories import user_payload

EMAIL = "new.viewer@example.com"
PASSWORD = "correct horse battery"


def register(client: TestClient, email: str = EMAIL, password: str = PASSWORD) -> Any:
    return client.post("/auth/register", json={"email": email, "password": password})


def login(client: TestClient, email: str = EMAIL, password: str = PASSWORD) -> Any:
    return client.post("/auth/login", json={"email": email, "password": password})


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def signed_token(**claims: Any) -> str:
    """Build a token with the real secret but custom claims (e.g. an old exp)."""
    now = datetime.now(timezone.utc)
    payload = {"sub": "1", "role": "admin", "iat": now, "exp": now + timedelta(minutes=5)}
    payload.update(claims)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# --- Registration -------------------------------------------------------------


def test_register_returns_201_without_password(client: TestClient) -> None:
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"], "email": EMAIL, "role": "viewer"}
    assert PASSWORD not in response.text
    assert "hashed_password" not in body


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    register(client)

    response = register(client, email=EMAIL.upper())

    assert response.status_code == 409
    assert response.json()["detail"] == "This email already exists"


def test_password_is_stored_as_argon2_hash(client: TestClient, db_session: Session) -> None:
    register(client)

    account = db_session.scalars(select(Account).where(Account.email == EMAIL)).one()

    assert account.hashed_password != PASSWORD
    assert account.hashed_password.startswith("$argon2id$")
    assert PASSWORD not in account.hashed_password


def test_register_ignores_role_sent_by_client(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "role": "admin"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "viewer"


def test_register_rejects_short_password(client: TestClient) -> None:
    response = register(client, password="short")

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "password"
    assert "short" not in response.text  # the submitted value is never echoed


# --- Login ----------------------------------------------------------------------


def test_login_with_wrong_password_returns_401(client: TestClient) -> None:
    register(client)

    response = login(client, password="wrong password")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unknown_email_gets_same_error_as_wrong_password(client: TestClient) -> None:
    register(client)

    wrong_password = login(client, password="wrong password")
    unknown_email = login(client, email="nobody@example.com")

    assert unknown_email.status_code == wrong_password.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_login_returns_jwt_that_decodes(client: TestClient) -> None:
    account_id = register(client).json()["id"]

    response = login(client, email=EMAIL.upper())  # email is case-insensitive

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == JWT_EXPIRE_MINUTES * 60

    payload = jwt.decode(body["access_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == str(account_id)
    assert payload["role"] == "viewer"
    assert payload["exp"] - payload["iat"] == JWT_EXPIRE_MINUTES * 60


def test_me_returns_logged_in_account(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]

    response = client.get("/auth/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


# --- Tokens ----------------------------------------------------------------------


def test_users_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/users")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        # Signed with a different secret.
        jwt.encode({"sub": "1", "iat": 0, "exp": 9999999999}, "x" * 40, algorithm="HS256"),
        # alg "none": no signature at all. Must be refused, not trusted.
        jwt.encode({"sub": "1", "iat": 0, "exp": 9999999999}, None, algorithm="none"),
    ],
    ids=["garbage", "wrong-secret", "alg-none"],
)
def test_invalid_token_returns_401(client: TestClient, token: str) -> None:
    response = client.get("/users", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_tampered_payload_returns_401(client: TestClient, viewer_headers: dict[str, str]) -> None:
    """Editing the payload (viewer -> admin) breaks the signature."""
    header, payload, signature = viewer_headers["Authorization"].removeprefix("Bearer ").split(".")
    claims = jwt.utils.base64url_decode(payload)
    forged_payload = jwt.utils.base64url_encode(claims.replace(b'"viewer"', b'"admin"')).decode()

    response = client.delete("/users/1", headers=bearer(f"{header}.{forged_payload}.{signature}"))

    assert response.status_code == 401


def test_expired_token_returns_401(client: TestClient, admin_headers: dict[str, str]) -> None:
    # admin_headers creates account 1, so the only thing wrong is the expiry.
    now = datetime.now(timezone.utc)
    expired = signed_token(iat=now - timedelta(hours=1), exp=now - timedelta(seconds=1))

    response = client.get("/users", headers=bearer(expired))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_token_without_exp_returns_401(client: TestClient, admin_headers: dict[str, str]) -> None:
    # Account 1 exists (admin_headers): only the missing exp claim is wrong.
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "1", "iat": now}, JWT_SECRET, algorithm=JWT_ALGORITHM)

    assert client.get("/users", headers=bearer(token)).status_code == 401


def test_token_of_deleted_account_returns_401(client: TestClient, db_session: Session) -> None:
    account = Account(email="gone@example.com", hashed_password="x", role=Role.ADMIN.value)
    db_session.add(account)
    db_session.commit()
    token = create_access_token(account.id, account.role)
    db_session.delete(account)
    db_session.commit()

    assert client.get("/users", headers=bearer(token)).status_code == 401


# --- Roles -------------------------------------------------------------------


def test_viewer_can_read_users(viewer_client: TestClient, create_user: Any) -> None:
    user = create_user()

    assert viewer_client.get("/users").status_code == 200
    assert viewer_client.get(f"/users/{user['id']}").status_code == 200


def test_viewer_delete_returns_403(viewer_client: TestClient, create_user: Any) -> None:
    user = create_user()

    response = viewer_client.delete(f"/users/{user['id']}")

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to perform this action"


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/users", user_payload(email="other@example.com")),
        ("put", "/users/{id}", user_payload()),
        ("patch", "/users/{id}", {"city": "Quetta"}),
    ],
    ids=["POST", "PUT", "PATCH"],
)
def test_viewer_cannot_change_users(
    viewer_client: TestClient, create_user: Any, method: str, path: str, body: dict[str, Any]
) -> None:
    user = create_user()

    response = viewer_client.request(method, path.format(id=user["id"]), json=body)

    assert response.status_code == 403


def test_admin_delete_returns_204(admin_client: TestClient, create_user: Any) -> None:
    user = create_user()

    response = admin_client.delete(f"/users/{user['id']}")

    assert response.status_code == 204


def test_demoted_admin_loses_access_with_old_token(
    admin_client: TestClient, create_user: Any, db_session: Session
) -> None:
    """The role is read from the database on every request, not from the token."""
    user = create_user()
    admin = db_session.scalars(select(Account).where(Account.role == Role.ADMIN.value)).one()
    admin.role = Role.VIEWER.value
    db_session.commit()

    response = admin_client.delete(f"/users/{user['id']}")

    assert response.status_code == 403
