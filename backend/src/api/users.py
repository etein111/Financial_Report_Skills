"""
用户管理 API

处理用户的 CRUD 操作，包括创建、编辑、删除、搜索用户
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated, Optional
from ..models.user import (
    UserCreate, UserUpdate, UserResponse,
    ChangePasswordAdminRequest, UpdateRoleRequest,
    CheckEmailRequest, CheckEmailResponse
)
from ..core.security import get_current_user, require_admin
from ..core.supabase import get_supabase

router = APIRouter()
supabase = get_supabase()


def format_user_data(user) -> dict:
    """格式化用户数据"""
    from datetime import datetime

    app_metadata = user.app_metadata or {}
    user_metadata = user.user_metadata or {}

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user_metadata.get("full_name"),
        "role": app_metadata.get("role", "analyst"),
        "banned": user.banned or False,
        "created_at": user.created_at,
        "last_sign_in_at": user.last_sign_in_at
    }


@router.get("")
async def list_users(
    current_user: Annotated[dict, Depends(require_admin)],
    search: Optional[str] = Query(None, description="按邮箱或姓名搜索")
) -> dict:
    """
    获取用户列表

    只有 Admin 可以访问。支持按邮箱或姓名搜索。
    """
    try:
        # 使用 Supabase Admin API 列出用户
        result = supabase.auth.admin.list_users()

        users = result.users if hasattr(result, 'users') else []

        # 搜索过滤
        if search:
            search_lower = search.lower()
            users = [
                u for u in users
                if search_lower in u.email.lower() or
                search_lower in (u.user_metadata or {}).get("full_name", "").lower()
            ]

        # 格式化用户数据
        formatted_users = [format_user_data(u) for u in users]

        return {
            "success": True,
            "message": f"获取用户列表成功，共 {len(formatted_users)} 条",
            "data": formatted_users
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户列表失败: {str(e)}"
        )


@router.post("")
async def create_user(
    user_data: UserCreate,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    创建新用户

    只有 Admin 可以创建用户。
    """
    try:
        # 使用 Supabase Admin API 创建用户
        user = supabase.auth.admin.create_user({
            "email": user_data.email,
            "password": user_data.password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": user_data.full_name
            },
            "app_metadata": {
                "role": user_data.role,
                "provider": "email"
            }
        })

        return {
            "success": True,
            "message": "用户创建成功",
            "data": format_user_data(user)
        }

    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate" in error_msg or "already" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该邮箱已被注册"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建用户失败: {str(e)}"
        )


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    更新用户信息

    只有 Admin 可以更新用户信息。
    """
    try:
        # 获取现有用户
        result = supabase.auth.admin.get_user_by_id(user_id)
        if not result or not result.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        existing_user = result.user

        # 准备更新数据
        update_data = {
            "user_metadata": {
                **(existing_user.user_metadata or {}),
                "full_name": user_data.full_name if user_data.full_name is not None
                    else existing_user.user_metadata.get("full_name")
            }
        }

        if user_data.email is not None:
            update_data["email"] = user_data.email

        # 更新用户
        updated_user = supabase.auth.admin.update_user_by_id(
            user_id,
            update_data
        )

        return {
            "success": True,
            "message": "用户更新成功",
            "data": format_user_data(updated_user)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户失败: {str(e)}"
        )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    删除用户

    只有 Admin 可以删除用户。
    """
    try:
        # 删除用户
        supabase.auth.admin.delete_user(user_id)

        return {
            "success": True,
            "message": "用户删除成功",
            "data": {"id": user_id}
        }

    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除用户失败: {str(e)}"
        )


@router.post("/check-email", response_model=CheckEmailResponse)
async def check_email(
    request: CheckEmailRequest,
    current_user: Annotated[dict, Depends(require_admin)]
) -> CheckEmailResponse:
    """
    检查邮箱是否已被注册

    用于前端实时验证邮箱唯一性。
    """
    try:
        # 列出所有用户并检查邮箱
        result = supabase.auth.admin.list_users()
        users = result.users if hasattr(result, 'users') else []

        exists = any(u.email == request.email for u in users)

        return CheckEmailResponse(exists=exists)

    except Exception:
        # 出错时返回 False 以避免阻止正常注册
        return CheckEmailResponse(exists=False)


@router.put("/{user_id}/password")
async def change_user_password(
    user_id: str,
    request: ChangePasswordAdminRequest,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    修改用户密码

    只有 Admin 可以修改其他用户的密码。
    """
    try:
        # 使用 Supabase Admin API 修改密码
        updated_user = supabase.auth.admin.update_user_by_id(
            user_id,
            {"password": request.new_password}
        )

        return {
            "success": True,
            "message": "密码修改成功",
            "data": format_user_data(updated_user)
        }

    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改密码失败: {str(e)}"
        )


@router.put("/{user_id}/role")
async def change_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    修改用户角色

    只有 Admin 可以修改用户角色。
    """
    try:
        # 获取现有用户
        result = supabase.auth.admin.get_user_by_id(user_id)
        if not result or not result.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        existing_user = result.user

        # 更新 app_metadata 中的角色
        updated_user = supabase.auth.admin.update_user_by_id(
            user_id,
            {
                "app_metadata": {
                    **(existing_user.app_metadata or {}),
                    "role": request.role
                }
            }
        )

        return {
            "success": True,
            "message": "角色修改成功",
            "data": format_user_data(updated_user)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改角色失败: {str(e)}"
        )


@router.put("/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: str,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    启用/禁用用户账号

    只有 Admin 可以启用或禁用用户账号。
    """
    try:
        # 获取现有用户
        result = supabase.auth.admin.get_user_by_id(user_id)
        if not result or not result.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        existing_user = result.user
        new_banned_status = not (existing_user.banned or False)

        # 更新用户状态
        updated_user = supabase.auth.admin.update_user_by_id(
            user_id,
            {"banned": new_banned_status}
        )

        action = "禁用" if new_banned_status else "启用"

        return {
            "success": True,
            "message": f"用户{action}成功",
            "data": format_user_data(updated_user)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户状态失败: {str(e)}"
        )
