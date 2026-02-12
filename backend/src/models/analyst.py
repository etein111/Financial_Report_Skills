"""
Analyst 信息数据模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class AnalystBase(BaseModel):
    """Analyst 基础模型"""
    full_name: str = Field(..., min_length=1, max_length=200)
    chinese_name: Optional[str] = Field(None, max_length=200)
    email: EmailStr
    suffix: Optional[str] = Field(None, max_length=50)
    region_id: Optional[UUID] = None
    sfc: Optional[str] = Field(None, max_length=50)


class AnalystCreate(AnalystBase):
    """创建 Analyst 信息"""
    pass


class AnalystUpdate(BaseModel):
    """更新 Analyst 信息"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    chinese_name: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    suffix: Optional[str] = Field(None, max_length=50)
    region_id: Optional[UUID] = None
    sfc: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class AnalystResponse(AnalystBase):
    """Analyst 响应"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    region: Optional[dict] = None  # 关联的 region 信息

    class Config:
        from_attributes = True


class CheckEmailRequest(BaseModel):
    """检查邮箱唯一性"""
    email: EmailStr


class CheckEmailResponse(BaseModel):
    """邮箱检查响应"""
    exists: bool
