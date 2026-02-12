"""
用户管理数据模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    """创建用户"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    role: Literal["admin", "sa", "analyst"] = "analyst"


class UserUpdate(BaseModel):
    """更新用户"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    banned: bool = False
    created_at: datetime
    last_sign_in_at: Optional[datetime] = None


class ChangePasswordAdminRequest(BaseModel):
    """管理员修改用户密码"""
    new_password: str = Field(..., min_length=6)


class UpdateRoleRequest(BaseModel):
    """更新用户角色"""
    role: Literal["admin", "sa", "analyst"]


class CheckEmailRequest(BaseModel):
    """检查邮箱唯一性"""
    email: EmailStr


class CheckEmailResponse(BaseModel):
    """邮箱检查响应"""
    exists: bool
