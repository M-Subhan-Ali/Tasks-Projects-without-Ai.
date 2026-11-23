"""Business rules for users.

This layer knows nothing about HTTP: it never imports FastAPI and never raises
HTTPException. It raises application exceptions from app.exceptions instead.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.exceptions import EmailAlreadyExists, UserNotFound
from app.models import User
from app.repositories import user_repository
from app.schemas import UserCreate


def list_users(db: Session) -> list[User]:
    return user_repository.get_active_users(db)


def get_user(db: Session, user_id: int) -> User:
    user = user_repository.get_active_user_by_id(db, user_id)

    if user is None:
        raise UserNotFound(user_id)

    return user


def create_user(db: Session, user_data: UserCreate) -> User:
    _ensure_email_available(db, user_data.email)

    user = User(
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        city=user_data.city,
        company_name=user_data.company.name,
    )

    return user_repository.add_user(db, user)


def replace_user(db: Session, user_id: int, user_data: UserCreate) -> User:
    user = get_user(db, user_id)
    _ensure_email_available(db, user_data.email, exclude_user_id=user_id)

    user.name = user_data.name
    user.email = user_data.email
    user.phone = user_data.phone
    user.city = user_data.city
    user.company_name = user_data.company.name

    return user_repository.save_user(db, user)


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)

    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)

    user_repository.save_user(db, user)


def _ensure_email_available(
    db: Session, email: str, exclude_user_id: int | None = None
) -> None:
    if user_repository.email_exists(db, email, exclude_user_id):
        raise EmailAlreadyExists(email)
