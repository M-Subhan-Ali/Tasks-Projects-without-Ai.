import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

NAME_PATTERN = r"^[A-Za-z\s.'-]+$"
PHONE_PATTERN = r"^\+?[0-9\s()-]+$"


class Company(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=20)
    company: Company

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.fullmatch(NAME_PATTERN, value):
            raise ValueError("Name can only contain letters, spaces, . ' -")

        return value

    @field_validator("email")
    @classmethod
    def validate_email_length(cls, value: str) -> str:
        if len(value) > 100:
            raise ValueError("Email must be at most 100 characters")

        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not re.fullmatch(PHONE_PATTERN, value):
            raise ValueError("Phone number can only contain digits, spaces, + - ( )")

        digits = re.sub(r"\D", "", value)

        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("Phone number must have 7 to 15 digits")

        return value


class CompanyResponse(BaseModel):
    name: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    company: CompanyResponse
