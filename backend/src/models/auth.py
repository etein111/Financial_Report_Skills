"""
认证相关数据模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    message: str
    data: Optional[dict] = None


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=6)


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    token: str
    new_password: str = Field(..., min_length=6)
