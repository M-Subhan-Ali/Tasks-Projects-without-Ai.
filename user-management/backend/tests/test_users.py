"""API tests for /users. Each test starts with an empty database (see conftest.py)."""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import user_repository
from app.services import user_service
from tests.factories import user_payload

CreateUser = Callable[..., dict[str, Any]]


def error_fields(response_json: dict[str, Any]) -> set[str]:
    return {error["field"] for error in response_json["errors"]}


# --- The 9 required tests ----------------------------------------------------


def test_create_valid_user_returns_201_and_user(client: TestClient) -> None:
    response = client.post("/users", json=user_payload())

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["name"] == "Ali Raza"
    assert body["email"] == "ali.raza@example.com"
    assert body["city"] == "Lahore"
    assert body["company"] == {"name": "Cloud Pacer"}


def test_create_user_without_name_returns_validation_error(client: TestClient) -> None:
    payload = user_payload()
    del payload["name"]

    response = client.post("/users", json=payload)

    assert response.status_code == 422
    assert "name" in error_fields(response.json())


def test_create_user_with_invalid_email_returns_validation_error(client: TestClient) -> None:
    response = client.post("/users", json=user_payload(email="not-an-email"))

    assert response.status_code == 422
    assert "email" in error_fields(response.json())


def test_create_user_with_existing_email_returns_409(
    client: TestClient, create_user: CreateUser
) -> None:
    create_user(email="taken@example.com")

    response = client.post("/users", json=user_payload(email="taken@example.com"))

    assert response.status_code == 409
    assert response.json()["detail"] == "This email already exists"


def test_get_missing_user_returns_404(client: TestClient) -> None:
    response = client.get("/users/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_patch_updates_only_given_fields(client: TestClient, create_user: CreateUser) -> None:
    original = create_user()

    response = client.patch(f"/users/{original['id']}", json={"city": "Quetta"})

    assert response.status_code == 200
    updated = response.json()
    assert updated["city"] == "Quetta"
    # Everything that was not sent must be unchanged.
    for field in ("name", "email", "phone", "company"):
        assert updated[field] == original[field]
    # And the change was really saved, not just echoed back.
    assert client.get(f"/users/{original['id']}").json() == updated


def test_delete_returns_204_then_get_returns_404(
    client: TestClient, create_user: CreateUser
) -> None:
    user = create_user()

    delete_response = client.delete(f"/users/{user['id']}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert client.get(f"/users/{user['id']}").status_code == 404


def test_search_returns_only_matching_users(client: TestClient, create_user: CreateUser) -> None:
    create_user(name="John Smith", email="john@example.com")
    create_user(name="Sarah Lee", email="sarah@example.com")
    create_user(name="Mary Jones", email="johnny.fan@example.com")  # matches by email

    response = client.get("/users", params={"search": "john"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {user["email"] for user in body["items"]} == {
        "john@example.com",
        "johnny.fan@example.com",
    }


def test_pagination_returns_correct_total_and_page_size(
    client: TestClient, create_user: CreateUser
) -> None:
    for number in range(7):
        create_user(name=f"User {chr(65 + number)}", email=f"user{number}@example.com")

    first_page = client.get("/users", params={"page": 1, "limit": 5}).json()
    second_page = client.get("/users", params={"page": 2, "limit": 5}).json()

    assert first_page["total"] == 7
    assert len(first_page["items"]) == 5
    assert (first_page["page"], first_page["limit"]) == (1, 5)
    assert second_page["total"] == 7
    assert len(second_page["items"]) == 2
    # No user appears on both pages.
    first_ids = {user["id"] for user in first_page["items"]}
    second_ids = {user["id"] for user in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)


# --- Extra coverage for behaviour built in earlier phases -------------------


def test_validation_error_lists_every_invalid_field(client: TestClient) -> None:
    response = client.post("/users", json=user_payload(name="", email="bad", phone="abc"))

    assert response.status_code == 422
    assert {"name", "email", "phone"} <= error_fields(response.json())


def test_duplicate_email_check_ignores_case(client: TestClient, create_user: CreateUser) -> None:
    create_user(email="case@example.com")

    response = client.post("/users", json=user_payload(email="CASE@Example.com"))

    assert response.status_code == 409


@pytest.mark.parametrize("params", [{"page": 0}, {"limit": 0}, {"limit": 51}])
def test_invalid_pagination_params_return_422(client: TestClient, params: dict[str, int]) -> None:
    assert client.get("/users", params=params).status_code == 422


def test_patch_with_duplicate_email_returns_409(
    client: TestClient, create_user: CreateUser
) -> None:
    create_user(email="first@example.com")
    second = create_user(email="second@example.com")

    response = client.patch(f"/users/{second['id']}", json={"email": "first@example.com"})

    assert response.status_code == 409


def test_concurrent_duplicate_insert_returns_409_not_500(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate the race: the pre-check says the email is free, but another
    request already saved it. The database UNIQUE constraint must catch it."""
    db_session.add(
        User(name="Other", email="race@example.com", phone="0321-1234567", company_name="X")
    )
    db_session.commit()
    monkeypatch.setattr(user_repository, "email_exists", lambda *args, **kwargs: False)

    response = client.post("/users", json=user_payload(email="race@example.com"))

    assert response.status_code == 409


def test_unexpected_error_returns_generic_500_with_request_id(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def crash(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(user_service, "get_user", crash)

    response = client.get("/users/1")

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "secret" not in response.text
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_valid_client_request_id_is_reused(client: TestClient) -> None:
    request_id = str(uuid.uuid4())

    response = client.get("/users", headers={"X-Request-ID": request_id})

    assert response.headers["X-Request-ID"] == request_id


def test_invalid_client_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/users", headers={"X-Request-ID": "not-a-uuid"})

    returned_id = response.headers["X-Request-ID"]
    assert returned_id != "not-a-uuid"
    uuid.UUID(returned_id)  # raises if it is not a valid UUID
