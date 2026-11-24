"""HTTP layer for /auth: receive the request, call the service, return a response."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import JWT_EXPIRE_MINUTES
from app.database import get_db
from app.dependencies import CurrentAccount
from app.schemas import AccountResponse, LoginRequest, RegisterRequest, TokenResponse
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


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: DbSession) -> TokenResponse:
    token = auth_service.login(db, data)
    return TokenResponse(access_token=token, expires_in=JWT_EXPIRE_MINUTES * 60)


@router.get("/me", response_model=AccountResponse)
def me(account: CurrentAccount) -> AccountResponse:
    return AccountResponse.model_validate(account)
