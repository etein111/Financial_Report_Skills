"""
安全相关功能

JWT Token 验证和依赖注入
"""
from typing import Optional, Annotated
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from .config import settings

# HTTP Bearer 认证
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT Access Token

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量

    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    验证 JWT Token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的 payload

    Raises:
        HTTPException: Token 无效或过期
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> str:
    """
    从 JWT Token 中获取当前用户 ID

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        用户 ID

    Raises:
        HTTPException: Token 无效或过期
    """
    token = credentials.credentials
    payload = verify_token(token)

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token payload",
        )

    return user_id


def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> dict:
    """
    从 JWT Token 中获取当前用户完整信息

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        用户信息字典

    Raises:
        HTTPException: Token 无效或过期
    """
    token = credentials.credentials
    payload = verify_token(token)

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token payload",
        )

    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "analyst"),
        "full_name": payload.get("full_name"),
    }


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
