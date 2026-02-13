from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AnalystCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=128)
    chinese_name: str | None = Field(default=None, max_length=128)
    email: EmailStr
    region: str = Field(min_length=1)
    is_active: bool = True


class AnalystUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=128)
    chinese_name: str | None = Field(default=None, max_length=128)
    email: EmailStr | None = None
    region: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class AnalystCheckEmailRequest(BaseModel):
    email: EmailStr
    exclude_id: str | None = None


class AnalystItem(BaseModel):
    id: str
    full_name: str
    chinese_name: str | None = None
    email: str
    region_id: str | None = None
    region_name: str | None = None
    is_active: bool
    created_at: datetime | None = None

