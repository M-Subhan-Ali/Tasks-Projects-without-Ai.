from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Company(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=50)
    company: Company


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    company: Company
