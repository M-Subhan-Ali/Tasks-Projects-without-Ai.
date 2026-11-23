import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.exceptions import AppError, EmailAlreadyExists, UserNotFound
from app.routers import users

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


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    # Phase 4 changes this to return 422 with ALL invalid fields.
    first_error = error.errors()[0]
    field = ".".join(str(part) for part in first_error["loc"][1:])
    message = first_error["msg"].removeprefix("Value error, ")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"{field}: {message}"},
    )


app.include_router(users.router)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"message": "User Management API is running"}
