"""
安全相关功能

Supabase Auth JWT Token 验证和依赖注入
"""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .supabase import get_supabase

# HTTP Bearer 认证
security = HTTPBearer()

# Supabase 客户端（用于验证 token）
supabase_client = get_supabase()


def verify_supabase_token(token: str) -> dict:
    """
    验证 Supabase Auth JWT Token

    Args:
        token: Supabase Auth JWT token 字符串

    Returns:
        解码后的用户信息

    Raises:
        HTTPException: Token 无效或过期
    """
    try:
        # 使用 Supabase 客户端验证 token
        user_response = supabase_client.auth.get_user(jwt=token)

        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据"
            )

        user = user_response.user

        # 从 app_metadata 获取角色
        app_metadata = user.app_metadata or {}
        user_metadata = user.user_metadata or {}

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user_metadata.get("full_name"),
            "role": app_metadata.get("role", "analyst"),
        }
    except Exception as e:
        # 如果是 401 或 404，说明 token 无效
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> str:
    """
    从 Supabase Auth JWT Token 中获取当前用户 ID

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        用户 ID

    Raises:
        HTTPException: Token 无效或过期
    """
    token = credentials.credentials
    user_info = verify_supabase_token(token)

    user_id: str = user_info.get("id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token payload",
        )

    return user_id


def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> dict:
    """
    从 Supabase Auth JWT Token 中获取当前用户完整信息

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        用户信息字典

    Raises:
        HTTPException: Token 无效或过期
    """
    token = credentials.credentials
    return verify_supabase_token(token)


def require_admin(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """
    要求当前用户必须是 Admin

    Args:
        current_user: 当前用户信息

    Returns:
        用户信息字典

    Raises:
        HTTPException: 用户不是 Admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 Admin 权限"
        )
    return current_user
