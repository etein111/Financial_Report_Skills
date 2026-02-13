from datetime import datetime

from pydantic import BaseModel, Field


class RegionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=32)


class RegionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    code: str | None = Field(default=None, min_length=1, max_length=32)


class RegionItem(BaseModel):
    id: str
    name: str
    code: str
    created_at: datetime | None = None

