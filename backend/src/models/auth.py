from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class CurrentUser(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    is_active: bool = True
    access_token: str

