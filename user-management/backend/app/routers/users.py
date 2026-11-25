"""HTTP layer for /users: receive the request, call the service, return a response.

No database queries and no business rules here.

Access:
- every route needs a valid token (router-level dependency): viewers can read;
- routes that change data also need the admin role (require_role).

Webhooks: after a user is created, updated or deleted SUCCESSFULLY, the event
is queued as a background task (sent after the response). If the service
raises (404, 409...), the line that queues it is never reached, so no event.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_db, get_session_factory
from app.dependencies import get_current_account, require_role
from app.models import Role, WebhookEvent
from app.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services import user_service, webhook_delivery

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_account)],
)

DbSession = Annotated[Session, Depends(get_db)]
SessionFactory = Annotated[sessionmaker[Session], Depends(get_session_factory)]
ADMIN_ONLY = [Depends(require_role(Role.ADMIN))]


def _queue_webhook(
    background_tasks: BackgroundTasks,
    session_factory: sessionmaker[Session],
    event: WebhookEvent,
    user: UserResponse,
) -> None:
    background_tasks.add_task(
        webhook_delivery.deliver_event, session_factory, event.value, user.model_dump()
    )


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


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=ADMIN_ONLY,
)
def create_user(
    user_data: UserCreate,
    db: DbSession,
    background_tasks: BackgroundTasks,
    session_factory: SessionFactory,
) -> UserResponse:
    user = UserResponse.from_model(user_service.create_user(db, user_data))
    _queue_webhook(background_tasks, session_factory, WebhookEvent.USER_CREATED, user)
    return user


@router.put("/{user_id}", response_model=UserResponse, dependencies=ADMIN_ONLY)
def replace_user(
    user_id: int,
    user_data: UserCreate,
    db: DbSession,
    background_tasks: BackgroundTasks,
    session_factory: SessionFactory,
) -> UserResponse:
    user = UserResponse.from_model(user_service.replace_user(db, user_id, user_data))
    _queue_webhook(background_tasks, session_factory, WebhookEvent.USER_UPDATED, user)
    return user


@router.patch("/{user_id}", response_model=UserResponse, dependencies=ADMIN_ONLY)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: DbSession,
    background_tasks: BackgroundTasks,
    session_factory: SessionFactory,
) -> UserResponse:
    user = UserResponse.from_model(user_service.update_user(db, user_id, user_data))
    _queue_webhook(background_tasks, session_factory, WebhookEvent.USER_UPDATED, user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=ADMIN_ONLY,
)
def delete_user(
    user_id: int,
    db: DbSession,
    background_tasks: BackgroundTasks,
    session_factory: SessionFactory,
) -> Response:
    # The event carries the user as it was when deleted.
    user = UserResponse.from_model(user_service.delete_user(db, user_id))
    _queue_webhook(background_tasks, session_factory, WebhookEvent.USER_DELETED, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
