"""HTTP layer for /users: receive the request, call the service, return a response.

No database queries and no business rules here.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UserCreate, UserResponse
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)) -> list[UserResponse]:
    users = user_service.list_users(db)
    return [UserResponse.from_model(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    return UserResponse.from_model(user_service.get_user(db, user_id))


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    return UserResponse.from_model(user_service.create_user(db, user_data))


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserResponse.from_model(user_service.replace_user(db, user_id, user_data))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> Response:
    user_service.delete_user(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
