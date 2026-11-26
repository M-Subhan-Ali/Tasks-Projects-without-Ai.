"""API tests for /users. Each test starts with an empty database (see conftest.py).

These tests check user behaviour, so they run as an admin (admin_client).
Access rules for viewers and anonymous clients are tested in test_auth.py.
"""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import user_repository
from app.services import user_service
from tests.factories import user_payload

CreateUser = Callable[..., dict[str, Any]]


def error_fields(response_json: dict[str, Any]) -> set[str]:
    return {error["field"] for error in response_json["errors"]}


# --- The 9 required tests ----------------------------------------------------


def test_create_valid_user_returns_201_and_user(admin_client: TestClient) -> None:
    response = admin_client.post("/users", json=user_payload())

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["name"] == "Ali Raza"
    assert body["email"] == "ali.raza@example.com"
    assert body["city"] == "Lahore"
    assert body["company"] == {"name": "Cloud Pacer"}


def test_create_user_without_name_returns_validation_error(admin_client: TestClient) -> None:
    payload = user_payload()
    del payload["name"]

    response = admin_client.post("/users", json=payload)

    assert response.status_code == 422
    assert "name" in error_fields(response.json())


def test_create_user_with_invalid_email_returns_validation_error(admin_client: TestClient) -> None:
    response = admin_client.post("/users", json=user_payload(email="not-an-email"))

    assert response.status_code == 422
    assert "email" in error_fields(response.json())


def test_create_user_with_existing_email_returns_409(
    admin_client: TestClient, create_user: CreateUser
) -> None:
    create_user(email="taken@example.com")

    response = admin_client.post("/users", json=user_payload(email="taken@example.com"))

    assert response.status_code == 409
    assert response.json()["detail"] == "This email already exists"


def test_get_missing_user_returns_404(admin_client: TestClient) -> None:
    response = admin_client.get("/users/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_patch_updates_only_given_fields(admin_client: TestClient, create_user: CreateUser) -> None:
    original = create_user()

    response = admin_client.patch(f"/users/{original['id']}", json={"city": "Quetta"})

    assert response.status_code == 200
    updated = response.json()
    assert updated["city"] == "Quetta"
    # Everything that was not sent must be unchanged.
    for field in ("name", "email", "phone", "company"):
        assert updated[field] == original[field]
    # And the change was really saved, not just echoed back.
    assert admin_client.get(f"/users/{original['id']}").json() == updated


def test_delete_returns_204_then_get_returns_404(
    admin_client: TestClient, create_user: CreateUser
) -> None:
    user = create_user()

    delete_response = admin_client.delete(f"/users/{user['id']}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert admin_client.get(f"/users/{user['id']}").status_code == 404


def test_search_returns_only_matching_users(admin_client: TestClient, create_user: CreateUser) -> None:
    create_user(name="John Smith", email="john@example.com")
    create_user(name="Sarah Lee", email="sarah@example.com")
    create_user(name="Mary Jones", email="johnny.fan@example.com")  # matches by email

    response = admin_client.get("/users", params={"search": "john"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {user["email"] for user in body["items"]} == {
        "john@example.com",
        "johnny.fan@example.com",
    }


def test_pagination_returns_correct_total_and_page_size(
    admin_client: TestClient, create_user: CreateUser
) -> None:
    for number in range(7):
        create_user(name=f"User {chr(65 + number)}", email=f"user{number}@example.com")

    first_page = admin_client.get("/users", params={"page": 1, "limit": 5}).json()
    second_page = admin_client.get("/users", params={"page": 2, "limit": 5}).json()

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


def test_validation_error_lists_every_invalid_field(admin_client: TestClient) -> None:
    response = admin_client.post("/users", json=user_payload(name="", email="bad", phone="abc"))

    assert response.status_code == 422
    assert {"name", "email", "phone"} <= error_fields(response.json())


def test_duplicate_email_check_ignores_case(admin_client: TestClient, create_user: CreateUser) -> None:
    create_user(email="case@example.com")

    response = admin_client.post("/users", json=user_payload(email="CASE@Example.com"))

    assert response.status_code == 409


@pytest.mark.parametrize("params", [{"page": 0}, {"limit": 0}, {"limit": 51}])
def test_invalid_pagination_params_return_422(admin_client: TestClient, params: dict[str, int]) -> None:
    assert admin_client.get("/users", params=params).status_code == 422


def test_patch_with_duplicate_email_returns_409(
    admin_client: TestClient, create_user: CreateUser
) -> None:
    create_user(email="first@example.com")
    second = create_user(email="second@example.com")

    response = admin_client.patch(f"/users/{second['id']}", json={"email": "first@example.com"})

    assert response.status_code == 409


def test_concurrent_duplicate_insert_returns_409_not_500(
    admin_client: TestClient,
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

    response = admin_client.post("/users", json=user_payload(email="race@example.com"))

    assert response.status_code == 409


def test_unexpected_error_returns_generic_500_with_request_id(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def crash(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(user_service, "get_user", crash)

    response = admin_client.get("/users/1")

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "secret" not in response.text
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_valid_client_request_id_is_reused(admin_client: TestClient) -> None:
    request_id = str(uuid.uuid4())

    response = admin_client.get("/users", headers={"X-Request-ID": request_id})

    assert response.headers["X-Request-ID"] == request_id


def test_invalid_client_request_id_is_replaced(admin_client: TestClient) -> None:
    response = admin_client.get("/users", headers={"X-Request-ID": "not-a-uuid"})

    returned_id = response.headers["X-Request-ID"]
    assert returned_id != "not-a-uuid"
    uuid.UUID(returned_id)  # raises if it is not a valid UUID


# --- Reusing the email of a deleted user ----------------------------------------
# Emails are unique among ACTIVE users only (partial unique index
# uq_users_email_active, migration 0005).


def test_deleted_users_email_can_be_reused(admin_client: TestClient, create_user: CreateUser) -> None:
    # 1. Create a user: 201.
    original = create_user(email="reuse@example.com")

    # 2. Soft-delete that user: 204, and it is hidden.
    assert admin_client.delete(f"/users/{original['id']}").status_code == 204
    assert admin_client.get(f"/users/{original['id']}").status_code == 404

    # 3. Reuse the deleted user's email: 201, and it is a NEW user.
    response = admin_client.post("/users", json=user_payload(name="New Owner", email="reuse@example.com"))

    assert response.status_code == 201
    reused = response.json()
    assert reused["id"] != original["id"]
    assert reused["email"] == "reuse@example.com"
    listed = admin_client.get("/users").json()
    assert [user["id"] for user in listed["items"]] == [reused["id"]]


def test_active_users_email_still_returns_409_after_reuse(
    admin_client: TestClient, create_user: CreateUser
) -> None:
    deleted = create_user(email="taken.again@example.com")
    admin_client.delete(f"/users/{deleted['id']}")
    create_user(email="taken.again@example.com")  # the active owner now

    # 4. Duplicate an ACTIVE user's email: still 409.
    response = admin_client.post("/users", json=user_payload(email="taken.again@example.com"))

    assert response.status_code == 409
    assert response.json()["detail"] == "This email already exists"


def test_reuse_ignores_case(admin_client: TestClient, create_user: CreateUser) -> None:
    user = create_user(email="mixed@example.com")
    admin_client.delete(f"/users/{user['id']}")

    response = admin_client.post("/users", json=user_payload(email="MIXED@Example.com"))

    assert response.status_code == 201
    assert response.json()["email"] == "mixed@example.com"


def test_email_can_be_reused_more_than_once(admin_client: TestClient, create_user: CreateUser) -> None:
    for _ in range(3):
        user = create_user(email="many.times@example.com")
        assert admin_client.delete(f"/users/{user['id']}").status_code == 204

    assert admin_client.post("/users", json=user_payload(email="many.times@example.com")).status_code == 201


def test_update_can_take_a_deleted_users_email(admin_client: TestClient, create_user: CreateUser) -> None:
    deleted = create_user(email="old.owner@example.com")
    admin_client.delete(f"/users/{deleted['id']}")
    other = create_user(email="other.owner@example.com")

    patch = admin_client.patch(f"/users/{other['id']}", json={"email": "old.owner@example.com"})
    assert patch.status_code == 200
    assert patch.json()["email"] == "old.owner@example.com"

    # PUT gets the same rule.
    third = create_user(email="third@example.com")
    put = admin_client.put(f"/users/{third['id']}", json=user_payload(email="other.owner@example.com"))
    assert put.status_code == 200


def test_update_to_an_active_users_email_still_returns_409(
    admin_client: TestClient, create_user: CreateUser
) -> None:
    create_user(email="active.one@example.com")
    second = create_user(email="active.two@example.com")

    response = admin_client.put(f"/users/{second['id']}", json=user_payload(email="active.one@example.com"))

    assert response.status_code == 409


def test_reuse_race_is_allowed_when_only_a_deleted_user_has_the_email(
    admin_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the service check skipped, only the database decides: a deleted
    row with the same email must NOT block the insert."""
    db_session.add(
        User(name="Gone", email="race.reuse@example.com", phone="0321-1234567",
             company_name="X", is_deleted=True)
    )
    db_session.commit()
    monkeypatch.setattr(user_repository, "email_exists", lambda *args, **kwargs: False)

    response = admin_client.post("/users", json=user_payload(email="race.reuse@example.com"))

    assert response.status_code == 201


# --- The partial unique index itself (no API, straight to the database) ---------


def _user_row(email: str, is_deleted: bool) -> User:
    return User(name="Row", email=email, phone="0321-1234567", company_name="X", is_deleted=is_deleted)


def test_index_allows_deleted_and_active_rows_with_same_email(db_session: Session) -> None:
    db_session.add_all([
        _user_row("shared@example.com", is_deleted=True),
        _user_row("shared@example.com", is_deleted=True),
        _user_row("shared@example.com", is_deleted=False),
    ])
    db_session.commit()  # does not raise

    assert db_session.query(User).filter_by(email="shared@example.com").count() == 3


def test_index_rejects_two_active_rows_with_same_email(db_session: Session) -> None:
    db_session.add(_user_row("dup@example.com", is_deleted=False))
    db_session.commit()

    db_session.add(_user_row("dup@example.com", is_deleted=False))
    with pytest.raises(IntegrityError, match="users.email"):
        db_session.commit()
    db_session.rollback()


def test_index_rejects_restoring_a_deleted_user_whose_email_was_taken(db_session: Session) -> None:
    """Un-deleting a row would make two ACTIVE users share an email: refused."""
    deleted = _user_row("restore@example.com", is_deleted=True)
    db_session.add_all([deleted, _user_row("restore@example.com", is_deleted=False)])
    db_session.commit()

    deleted.is_deleted = False
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
