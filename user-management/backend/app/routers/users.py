"""HTTP layer for /users: receive the request, call the service, return a response.

No database queries and no business rules here.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=UserListResponse)
def get_users(
    db: DbSession,
    search: Annotated[str | None, Query(max_length=100, description="Match name or email")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> UserListResponse:
    result = user_service.list_users(db, search, page, limit)

    return UserListResponse(
        items=[UserResponse.from_model(user) for user in result.users],
        total=result.total,
        page=result.page,
        limit=result.limit,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: DbSession) -> UserResponse:
    return UserResponse.from_model(user_service.get_user(db, user_id))


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: DbSession) -> UserResponse:
    return UserResponse.from_model(user_service.create_user(db, user_data))


@router.put("/{user_id}", response_model=UserResponse)
def replace_user(user_id: int, user_data: UserCreate, db: DbSession) -> UserResponse:
    return UserResponse.from_model(user_service.replace_user(db, user_id, user_data))


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_data: UserUpdate, db: DbSession) -> UserResponse:
    return UserResponse.from_model(user_service.update_user(db, user_id, user_data))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DbSession) -> Response:
    user_service.delete_user(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
