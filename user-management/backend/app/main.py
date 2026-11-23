import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.exceptions import AppError, EmailAlreadyExists, UserNotFound
from app.logging_config import configure_logging
from app.routers import users

configure_logging()
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Temporary: Alembic migrations replace this in Phase 6.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The ONE place where application exceptions become HTTP status codes.
APP_ERROR_STATUS_CODES: dict[type[AppError], int] = {
    UserNotFound: status.HTTP_404_NOT_FOUND,
    EmailAlreadyExists: status.HTTP_409_CONFLICT,
}


@app.exception_handler(AppError)
def app_error_handler(request: Request, error: AppError) -> JSONResponse:
    status_code = APP_ERROR_STATUS_CODES.get(
        type(error), status.HTTP_400_BAD_REQUEST
    )
    return JSONResponse(status_code=status_code, content={"detail": error.message})


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
    """Last line of defence: log the real error, tell the client nothing internal."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


app.include_router(users.router)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"message": "User Management API is running"}
