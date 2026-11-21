import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, select, text

from app.database import Base, SessionLocal, engine
from app.models import User
from app.routers import users

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

Base.metadata.create_all(bind=engine)


def add_missing_columns() -> None:
    """Add columns to a users table that was created before they existed."""
    existing_columns = {column["name"] for column in inspect(engine).get_columns("users")}

    with engine.begin() as connection:
        if "city" not in existing_columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN city VARCHAR(100) NOT NULL DEFAULT ''")
            )

        if "is_deleted" not in existing_columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE")
            )

        if "deleted_at" not in existing_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN deleted_at DATETIME"))


add_missing_columns()


def seed_users() -> None:
    with SessionLocal() as db:
        if db.scalars(select(User)).first() is not None:
            return

        db.add_all(
            [
                User(name="John Smith", email="john@example.com", phone="0300-1234567", city="Karachi", company_name="Tech Solutions"),
                User(name="Sarah Johnson", email="sarah@example.com", phone="0301-2345678", city="Lahore", company_name="Creative Studio"),
                User(name="David Brown", email="david@example.com", phone="0302-3456789", city="Islamabad", company_name="Data Systems"),
                User(name="Michael Wilson", email="michael@example.com", phone="0303-4567890", city="Rawalpindi", company_name="Cloud Works"),
                User(name="Emily Davis", email="emily@example.com", phone="0304-5678901", city="Faisalabad", company_name="Market Hub"),
                User(name="James Taylor", email="james@example.com", phone="0305-6789012", city="Multan", company_name="Finance Pro"),
            ]
        )
        db.commit()


seed_users()

app = FastAPI(title="User Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
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
