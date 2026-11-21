from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import CompanyResponse, UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


def to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        city=user.city,
        company=CompanyResponse(name=user.company_name),
    )


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)

    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


def check_email_available(db: Session, email: str, user_id: int | None = None) -> None:

    query = select(User).where(func.lower(User.email) == email.lower())

    if user_id is not None:
        query = query.where(User.id != user_id)

    if db.scalars(query).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email already exists",
        )


@router.get("", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)) -> list[UserResponse]:
    users = db.scalars(select(User).where(User.is_deleted.is_(False)).order_by(User.id)).all()

    return [to_response(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    return to_response(get_user_or_404(db, user_id))


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    check_email_available(db, user_data.email)

    user = User(
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        city=user_data.city,
        company_name=user_data.company.name,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    user = get_user_or_404(db, user_id)

    check_email_available(db, user_data.email, user_id)

    user.name = user_data.name
    user.email = user_data.email
    user.phone = user_data.phone
    user.city = user_data.city
    user.company_name = user_data.company.name

    db.commit()
    db.refresh(user)

    return to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> Response:
    user = get_user_or_404(db, user_id)

    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)

    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
