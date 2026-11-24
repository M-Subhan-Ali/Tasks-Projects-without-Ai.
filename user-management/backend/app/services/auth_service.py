"""Business rules for accounts and authentication.

Like user_service, this layer never imports FastAPI: it raises application
exceptions, and main.py turns them into HTTP responses.
"""

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import EmailAlreadyExists, InvalidCredentials, NotAuthenticated
from app.models import Account, Role
from app.repositories import account_repository
from app.schemas import LoginRequest, RegisterRequest
from app.security import (
    burn_password_check_time,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


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


def login(db: Session, data: LoginRequest) -> str:
    """Check the email and password and return a signed access token."""
    account = account_repository.get_by_email(db, data.email)

    if account is None:
        burn_password_check_time(data.password)
        raise InvalidCredentials()
    if not verify_password(account.hashed_password, data.password):
        raise InvalidCredentials()

    return create_access_token(account.id, account.role)


def get_account_from_token(db: Session, token: str) -> Account:
    """Return the account a token belongs to, or raise NotAuthenticated."""
    try:
        payload = decode_access_token(token)
        account_id = int(payload["sub"])
    except jwt.ExpiredSignatureError as error:
        raise NotAuthenticated("Token has expired") from error
    except (jwt.InvalidTokenError, ValueError) as error:
        raise NotAuthenticated("Invalid token") from error

    # The token can outlive the account (deleted after login), so check the database.
    account = account_repository.get_by_id(db, account_id)
    if account is None:
        raise NotAuthenticated("Invalid token")

    return account
