import re
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.models import User

NAME_PATTERN = r"^[A-Za-z\s.'-]+$"
PHONE_PATTERN = r"^\+?[0-9\s()-]+$"


# --- Reusable field rules -------------------------------------------------
# Defined once and shared by UserCreate (all required) and UserUpdate
# (all optional), so both schemas always validate the same way.


def _check_name(value: str) -> str:
    if not re.fullmatch(NAME_PATTERN, value):
        raise ValueError("Name can only contain letters, spaces, . ' -")
    return value


def _check_city(value: str) -> str:
    if not re.fullmatch(NAME_PATTERN, value):
        raise ValueError("City can only contain letters, spaces, . ' -")
    return value


def _normalize_email(value: str) -> str:
    if len(value) > 100:
        raise ValueError("Email must be at most 100 characters")
    # Lowercase so the database UNIQUE constraint is effectively case-insensitive.
    return value.lower()


def _check_phone(value: str) -> str:
    if not re.fullmatch(PHONE_PATTERN, value):
        raise ValueError("Phone number can only contain digits, spaces, + - ( )")

    digits = re.sub(r"\D", "", value)
    if len(digits) < 7 or len(digits) > 15:
        raise ValueError("Phone number must have 7 to 15 digits")

    return value


Name = Annotated[str, Field(min_length=2, max_length=100), AfterValidator(_check_name)]
City = Annotated[str, Field(min_length=2, max_length=100), AfterValidator(_check_city)]
Email = Annotated[EmailStr, AfterValidator(_normalize_email)]
Phone = Annotated[str, Field(min_length=1, max_length=20), AfterValidator(_check_phone)]


# --- Request schemas -------------------------------------------------------


class Company(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)


class UserCreate(BaseModel):
    """Body for POST and PUT: every field is required."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Name
    email: Email
    phone: Phone
    city: City
    company: Company


class UserUpdate(BaseModel):
    """Body for PATCH: every field is optional; only the ones sent are changed."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Name | None = None
    email: Email | None = None
    phone: Phone | None = None
    city: City | None = None
    company: Company | None = None

    @field_validator("*", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: Any) -> Any:
        # Validators don't run for fields that were left out, so this only
        # fires when the client sends e.g. {"name": null}. Leaving a field out
        # means "don't change it"; null would try to empty a required column.
        if value is None:
            raise ValueError("Field cannot be null; leave it out to keep the current value")
        return value


# --- Response schemas ------------------------------------------------------


class CompanyResponse(BaseModel):
    name: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    city: str
    company: CompanyResponse

    @classmethod
    def from_model(cls, user: User) -> "UserResponse":
        """Convert the flat database row into the nested API shape."""
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            city=user.city,
            company=CompanyResponse(name=user.company_name),
        )


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    limit: int
