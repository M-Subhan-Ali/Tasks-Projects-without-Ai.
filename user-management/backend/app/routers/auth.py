"""HTTP layer for /auth: receive the request, call the service, return a response."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AccountResponse, RegisterRequest
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
