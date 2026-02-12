"""
Region 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class RegionBase(BaseModel):
    """Region 基础模型"""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=10)


class RegionCreate(RegionBase):
    """创建 Region"""
    pass


class RegionUpdate(RegionBase):
    """更新 Region"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=10)


class RegionResponse(RegionBase):
    """Region 响应"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
