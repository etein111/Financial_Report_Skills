"""
认证 API

处理用户登录、登出、获取当前用户信息
"""
from fastapi import APIRouter, Depends
from ..models.auth import LoginRequest, LoginResponse
from ..core.security import create_access_token, get_current_user
from ..core.supabase import get_supabase
from ..core.config import settings
from typing import Annotated

router = APIRouter()
supabase = get_supabase()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录

    使用 Supabase Auth 进行身份验证，成功后返回 JWT token
    """
    try:
        # 使用 Supabase Auth 进行登录
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })

        if not auth_response.user:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )

        user = auth_response.user
        session = auth_response.session

        # 从 app_metadata 获取角色
        app_metadata = user.app_metadata or {}
        user_metadata = user.user_metadata or {}

        role = app_metadata.get("role", "analyst")
        full_name = user_metadata.get("full_name")

        # 创建 JWT token
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": role,
            "full_name": full_name,
        })

        return LoginResponse(
            success=True,
            message="登录成功",
            data={
                "token": access_token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": full_name,
                    "role": role,
                }
            }
        )

    except Exception as e:
        from fastapi import HTTPException, status
        error_msg = str(e).lower()
        if "invalid" in error_msg or "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.post("/logout")
async def logout():
    """
    用户登出

    注意：由于使用 JWT，客户端删除 token 即可
    如果需要，可以在此处实现 token 黑名单
    """
    return {
        "success": True,
        "message": "登出成功",
        "data": None
    }


@router.get("/me")
async def get_current_user_info(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    获取当前用户信息

    从 JWT token 中提取用户信息
    """
    return {
        "success": True,
        "message": "获取用户信息成功",
        "data": current_user
    }
