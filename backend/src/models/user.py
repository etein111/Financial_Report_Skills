from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=128)
    role: str = Field(default="analyst")


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=128)


class UserPasswordUpdate(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserRoleUpdate(BaseModel):
    role: str


class UserToggleStatusResponse(BaseModel):
    id: str
    is_active: bool


class UserItem(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    is_active: bool
    created_at: datetime | None = None

