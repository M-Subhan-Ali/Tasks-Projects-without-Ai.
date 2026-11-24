"""HTTP layer for /auth: receive the request, call the service, return a response."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.config import AUTH_COOKIE_NAME, COOKIE_SECURE, JWT_EXPIRE_MINUTES
from app.database import get_db
from app.dependencies import CurrentAccount
from app.schemas import AccountResponse, LoginRequest, RegisterRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/register",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(data: RegisterRequest, db: DbSession) -> AccountResponse:
    account = auth_service.register(db, data)
    # response_model only has id, email and role: the hash never leaves the server.
    return AccountResponse.model_validate(account)


@router.post("/login", response_model=AccountResponse)
def login(data: LoginRequest, db: DbSession, response: Response) -> AccountResponse:
    """Check the credentials and put the token in an httpOnly cookie.

    The token is NOT in the response body: JavaScript never sees it, so an
    XSS bug cannot steal it. The browser stores the cookie and sends it back
    automatically on every request to this API.
    """
    result = auth_service.login(db, data)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=result.access_token,
        max_age=JWT_EXPIRE_MINUTES * 60,  # the browser drops it when the token expires
        httponly=True,  # not readable from JavaScript (document.cookie)
        secure=COOKIE_SECURE,  # only sent over HTTPS (localhost counts as secure)
        samesite="strict",  # never sent on requests started by another site (CSRF)
        path="/",
    )
    return AccountResponse.model_validate(result.account)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Delete the cookie. Only the server can, because JavaScript cannot touch it.

    Public on purpose: logging out must work even with an expired token.
    """
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


@router.get("/me", response_model=AccountResponse)
def me(account: CurrentAccount) -> AccountResponse:
    return AccountResponse.model_validate(account)
