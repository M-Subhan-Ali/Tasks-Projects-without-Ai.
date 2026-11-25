"""Business rules for users.

This layer knows nothing about HTTP: it never imports FastAPI and never raises
HTTPException. It raises application exceptions from app.exceptions instead.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import EmailAlreadyExists, UserNotFound
from app.models import User
from app.repositories import user_repository
from app.schemas import UserCreate, UserUpdate

# Log IDs and field NAMES only, never the values (names, emails, phones).
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserPage:
    users: list[User]
    total: int
    page: int
    limit: int


def list_users(db: Session, search: str | None, page: int, limit: int) -> UserPage:
    search_text = search.strip() if search else None
    offset = (page - 1) * limit

    users, total = user_repository.search_active_users(db, search_text, offset, limit)

    return UserPage(users=users, total=total, page=page, limit=limit)


def get_user(db: Session, user_id: int) -> User:
    user = user_repository.get_active_user_by_id(db, user_id)

    if user is None:
        raise UserNotFound(user_id)

    return user


def create_user(db: Session, user_data: UserCreate) -> User:
    _ensure_email_available(db, user_data.email)

    user = User(**_to_column_values(user_data.model_dump()))

    try:
        user = user_repository.add_user(db, user)
    except IntegrityError as error:
        _raise_if_duplicate_email(error, user_data.email)
        raise

    logger.info("User created user_id=%s", user.id)
    return user


def replace_user(db: Session, user_id: int, user_data: UserCreate) -> User:
    """PUT: overwrite every field."""
    return _apply_changes(db, user_id, user_data.model_dump())


def update_user(db: Session, user_id: int, user_data: UserUpdate) -> User:
    """PATCH: change only the fields the client actually sent."""
    return _apply_changes(db, user_id, user_data.model_dump(exclude_unset=True))


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)

    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)

    user_repository.save_user(db, user)
    logger.info("User soft-deleted user_id=%s", user_id)


def _apply_changes(db: Session, user_id: int, changes: dict[str, Any]) -> User:
    user = get_user(db, user_id)

    new_email = changes.get("email")
    if new_email is not None:
        _ensure_email_available(db, new_email, exclude_user_id=user_id)

    for column, value in _to_column_values(changes).items():
        setattr(user, column, value)

    try:
        user = user_repository.save_user(db, user)
    except IntegrityError as error:
        _raise_if_duplicate_email(error, new_email or user.email)
        raise

    logger.info("User updated user_id=%s fields=%s", user_id, sorted(changes))
    return user


def _to_column_values(data: dict[str, Any]) -> dict[str, Any]:
    """Map the API shape ({"company": {"name": ...}}) to the table columns."""
    values = dict(data)

    if "company" in values:
        values["company_name"] = values.pop("company")["name"]

    return values


def _ensure_email_available(
    db: Session, email: str, exclude_user_id: int | None = None
) -> None:
    if user_repository.email_exists(db, email, exclude_user_id):
        logger.info("Rejected: email already used by another user")
        raise EmailAlreadyExists(email)


def _raise_if_duplicate_email(error: IntegrityError, email: str) -> None:
    """Handle the race where two requests both pass the email check.

    The database UNIQUE constraint is the final guard. If it was the email
    constraint that failed, report it as a normal duplicate (409). Any other
    integrity error is unexpected, so the caller re-raises it (500).
    """
    if "users.email" in str(error.orig):
        logger.warning("Duplicate email caught by the database UNIQUE constraint (race)")
        raise EmailAlreadyExists(email) from error
