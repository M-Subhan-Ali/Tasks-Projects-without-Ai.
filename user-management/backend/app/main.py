import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.exceptions import (
    AppError,
    EmailAlreadyExists,
    InvalidCredentials,
    NotAuthenticated,
    PermissionDenied,
    UnsafeWebhookUrl,
    UserNotFound,
    WebhookNotFound,
)
from app.logging_config import configure_logging
from app.middleware import REQUEST_ID_HEADER, request_logging_middleware
from app.routers import auth, users, webhooks

# The database schema is managed only by Alembic migrations:
#   alembic upgrade head
# The app no longer creates or alters tables on startup.

configure_logging()
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app = FastAPI(title="User Management API")

# Order matters: the LAST middleware added is the OUTERMOST layer.
# Request logging is added first so it sits INSIDE CORS, which means the
# 500 responses it creates still get CORS headers on the way out.
app.add_middleware(BaseHTTPMiddleware, dispatch=request_logging_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    # Needed so the browser sends and accepts the auth cookie. This is only
    # allowed together with an explicit origin list, never "*".
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],  # let frontend JS read the request ID
)

# The ONE place where application exceptions become HTTP status codes.
APP_ERROR_STATUS_CODES: dict[type[AppError], int] = {
    UserNotFound: status.HTTP_404_NOT_FOUND,
    WebhookNotFound: status.HTTP_404_NOT_FOUND,
    EmailAlreadyExists: status.HTTP_409_CONFLICT,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    NotAuthenticated: status.HTTP_401_UNAUTHORIZED,
    PermissionDenied: status.HTTP_403_FORBIDDEN,
    UnsafeWebhookUrl: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


@app.exception_handler(AppError)
def app_error_handler(request: Request, error: AppError) -> JSONResponse:
    status_code = APP_ERROR_STATUS_CODES.get(
        type(error), status.HTTP_400_BAD_REQUEST
    )
    # The HTTP spec requires a 401 to say which auth scheme the client should use.
    headers = (
        {"WWW-Authenticate": "Bearer"}
        if status_code == status.HTTP_401_UNAUTHORIZED
        else None
    )
    # An error about one field gets the same shape as Pydantic's 422s, so
    # clients show it the same way.
    content: dict[str, object] = (
        {"detail": "Validation failed", "errors": [{"field": error.field, "message": error.message}]}
        if error.field is not None
        else {"detail": error.message}
    )
    return JSONResponse(status_code=status_code, content=content, headers=headers)


def _format_validation_error(error: dict) -> dict[str, str]:
    # loc looks like ("body", "company", "name") or ("path", "user_id").
    # Drop the first part (where it came from) and join the rest.
    field = ".".join(str(part) for part in error["loc"][1:]) or str(error["loc"][0])
    message = error["msg"].removeprefix("Value error, ")
    return {"field": field, "message": message}


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    """Return 422 listing EVERY invalid field, not just the first one."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": "Validation failed",
            "errors": [_format_validation_error(item) for item in error.errors()],
        },
    )


@app.exception_handler(Exception)
def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    """Safety net only: errors in routes are caught by request_logging_middleware.

    This runs only if something fails outside it (e.g. in a middleware itself).
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(webhooks.router)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"message": "User Management API is running"}
