"""Database access for users. SQLAlchemy queries live here and nowhere else."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


def get_active_users(db: Session) -> list[User]:
    query = select(User).where(User.is_deleted.is_(False)).order_by(User.id)
    return list(db.scalars(query).all())


def get_active_user_by_id(db: Session, user_id: int) -> User | None:
    user = db.get(User, user_id)

    if user is None or user.is_deleted:
        return None

    return user


def email_exists(db: Session, email: str, exclude_user_id: int | None = None) -> bool:
    query = select(User.id).where(func.lower(User.email) == email.lower())

    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)

    return db.scalars(query).first() is not None


def add_user(db: Session, user: User) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save_user(db: Session, user: User) -> User:
    db.commit()
    db.refresh(user)
    return user
