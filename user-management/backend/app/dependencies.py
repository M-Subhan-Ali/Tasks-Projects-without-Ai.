"""Shared FastAPI dependencies for authentication and authorization.

401 Unauthorized = we don't know who you are (no token, bad token, expired).
403 Forbidden    = we know who you are, but your role may not do this.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import NotAuthenticated, PermissionDenied
from app.models import Account, Role
from app.services import auth_service

# auto_error=False: we raise NotAuthenticated ourselves, so a missing token gets
# the same 401 JSON shape as every other auth error. HTTPBearer also adds the
# "Authorize" button to Swagger UI (/docs).
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_account(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Account:
    """Read 'Authorization: Bearer <token>' and return the logged-in account."""
    if credentials is None:
        raise NotAuthenticated()

    return auth_service.get_account_from_token(db, credentials.credentials)


CurrentAccount = Annotated[Account, Depends(get_current_account)]


def require_role(*allowed_roles: Role) -> Callable[[Account], Account]:
    """Dependency factory: require_role(Role.ADMIN) only lets admins through.

    It builds on get_current_account, so authentication (401) is always
    checked before the role (403).
    """
    allowed = {role.value for role in allowed_roles}

    def check_role(account: CurrentAccount) -> Account:
        if account.role not in allowed:
            raise PermissionDenied()
        return account

    return check_role
