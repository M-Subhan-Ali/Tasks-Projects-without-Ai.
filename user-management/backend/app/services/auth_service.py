"""Business rules for accounts and authentication.

Like user_service, this layer never imports FastAPI: it raises application
exceptions, and main.py turns them into HTTP responses.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import EmailAlreadyExists
from app.models import Account, Role
from app.repositories import account_repository
from app.schemas import RegisterRequest
from app.security import hash_password


def register(db: Session, data: RegisterRequest) -> Account:
    """Create a viewer account. Admins are only created with scripts/create_admin.py,
    so nobody can make themselves an admin through the public API."""
    if account_repository.email_exists(db, data.email):
        raise EmailAlreadyExists(data.email)

    account = Account(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=Role.VIEWER.value,
    )

    try:
        return account_repository.add_account(db, account)
    except IntegrityError as error:
        # Race: another request registered the same email after our check.
        if "accounts.email" in str(error.orig):
            raise EmailAlreadyExists(data.email) from error
        raise
