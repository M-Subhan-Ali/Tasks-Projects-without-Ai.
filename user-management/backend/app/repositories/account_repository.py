"""Database access for accounts. SQLAlchemy queries live here and nowhere else."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Account


def email_exists(db: Session, email: str) -> bool:
    query = select(Account.id).where(func.lower(Account.email) == email.lower())
    return db.scalars(query).first() is not None


def add_account(db: Session, account: Account) -> Account:
    db.add(account)

    try:
        db.commit()
    except IntegrityError:
        # The session is unusable after a failed commit until it is rolled back.
        db.rollback()
        raise

    db.refresh(account)
    return account


def get_by_email(db: Session, email: str) -> Account | None:
    query = select(Account).where(func.lower(Account.email) == email.lower())
    return db.scalars(query).first()


def get_by_id(db: Session, account_id: int) -> Account | None:
    return db.get(Account, account_id)
