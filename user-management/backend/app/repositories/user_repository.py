"""Database access for users. SQLAlchemy queries live here and nowhere else."""

import logging

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User

logger = logging.getLogger(__name__)


def search_active_users(
    db: Session, search: str | None, offset: int, limit: int
) -> tuple[list[User], int]:
    """Return one page of matching users plus the total number of matches.

    Filtering, counting and paging all happen in SQL, so only `limit` rows
    are ever loaded into Python.
    """
    filters = _active_user_filters(search)

    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0

    page_query = (
        select(User).where(*filters).order_by(User.id).offset(offset).limit(limit)
    )
    users = list(db.scalars(page_query).all())

    # DEBUG only (LOG_LEVEL=DEBUG): helps check paging maths while developing.
    logger.debug(
        "Searched users search=%r offset=%d limit=%d -> %d of %d",
        search,
        offset,
        limit,
        len(users),
        total,
    )
    return users, total


def get_active_user_by_id(db: Session, user_id: int) -> User | None:
    user = db.get(User, user_id)

    if user is None or user.is_deleted:
        return None

    return user


def email_exists(db: Session, email: str, exclude_user_id: int | None = None) -> bool:
    """True if an ACTIVE user has this email. Deleted users' emails are free to reuse,
    matching the partial unique index uq_users_email_active."""
    query = select(User.id).where(
        func.lower(User.email) == email.lower(),
        User.is_deleted.is_(False),
    )

    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)

    return db.scalars(query).first() is not None


def add_user(db: Session, user: User) -> User:
    db.add(user)
    return _commit_and_refresh(db, user)


def save_user(db: Session, user: User) -> User:
    return _commit_and_refresh(db, user)


def _active_user_filters(search: str | None) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [User.is_deleted.is_(False)]

    if search:
        pattern = f"%{_escape_like(search)}%"
        filters.append(
            or_(
                User.name.ilike(pattern, escape="\\"),
                User.email.ilike(pattern, escape="\\"),
            )
        )

    return filters


def _escape_like(text: str) -> str:
    """Make % and _ in the search text match literally instead of as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _commit_and_refresh(db: Session, user: User) -> User:
    """Commit the session. On a constraint error, roll back and re-raise.

    The rollback is required: after a failed commit the session is unusable
    until it is rolled back.
    """
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(user)
    return user
