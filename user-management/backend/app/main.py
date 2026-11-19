import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import User
from app.routers import users

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

Base.metadata.create_all(bind=engine)


def seed_users() -> None:
    with SessionLocal() as db:
        if db.scalars(select(User)).first() is not None:
            return

        db.add_all(
            [
                User(name="John Smith", email="john@example.com", phone="0300-1234567", company_name="Tech Solutions"),
                User(name="Sarah Johnson", email="sarah@example.com", phone="0301-2345678", company_name="Creative Studio"),
                User(name="David Brown", email="david@example.com", phone="0302-3456789", company_name="Data Systems"),
                User(name="Michael Wilson", email="michael@example.com", phone="0303-4567890", company_name="Cloud Works"),
                User(name="Emily Davis", email="emily@example.com", phone="0304-5678901", company_name="Market Hub"),
                User(name="James Taylor", email="james@example.com", phone="0305-6789012", company_name="Finance Pro"),
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
    field = first_error["loc"][-1]

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"{field}: {first_error['msg']}"},
    )


app.include_router(users.router)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"message": "User Management API is running"}
