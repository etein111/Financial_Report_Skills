"""
用户管理 API

处理用户的 CRUD 操作，包括创建、编辑、删除、搜索用户
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated, Optional
from ..models.user import (
    UserCreate, UserUpdate, UserResponse,
    ChangePasswordAdminRequest, UpdateRoleRequest,
    CheckEmailRequest, CheckEmailResponse
)
from ..core.security import get_current_user, require_admin
from ..core.config import settings

router = APIRouter()


async def call_supabase_admin_api(method: str, path: str, data: dict = None) -> dict:
    """调用 Supabase Admin API"""
    url = f"{settings.SUPABASE_URL}/auth/v1{path}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            response = await client.get(url, headers=headers)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = await client.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        if response.status_code >= 400:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("message", error_detail)
            except:
                pass
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json() if response.text else {}


def format_user_dict(user: dict) -> dict:
    """格式化用户数据（从字典）"""
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "full_name": user.get("user_metadata", {}).get("full_name"),
        "role": user.get("app_metadata", {}).get("role", "analyst"),
        "banned": user.get("banned", False),
        "created_at": user.get("created_at"),
        "last_sign_in_at": user.get("last_sign_in_at")
    }


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
        # 调用 Supabase Admin API
        result = await call_supabase_admin_api("GET", "/admin/users")

        # Supabase 返回格式: {"users": [...], "aud": "..."}
        users = result.get("users", [])

        # 搜索过滤
        if search:
            search_lower = search.lower()
            users = [
                u for u in users
                if search_lower in u.get("email", "").lower() or
                search_lower in u.get("user_metadata", {}).get("full_name", "").lower()
            ]

        # 格式化用户数据
        formatted_users = [format_user_dict(u) for u in users]

        return {
            "success": True,
            "message": f"获取用户列表成功，共 {len(formatted_users)} 条",
            "data": formatted_users
        }

    except HTTPException:
        raise
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
        # 调用 Supabase Admin API 创建用户
        user = await call_supabase_admin_api("POST", "/admin/users", {
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
            "data": format_user_dict(user)
        }

    except HTTPException as e:
        if e.status_code == 409 or "already" in str(e.detail):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该邮箱已被注册"
            )
        raise
    except Exception as e:
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
        result = await call_supabase_admin_api("GET", f"/admin/users/{user_id}")
        existing_user = result

        # 准备更新数据
        update_data = {
            "user_metadata": {
                **existing_user.get("user_metadata", {}),
                "full_name": user_data.full_name if user_data.full_name is not None
                    else existing_user.get("user_metadata", {}).get("full_name")
            }
        }

        if user_data.email is not None:
            update_data["email"] = user_data.email

        # 更新用户
        updated_user = await call_supabase_admin_api("PUT", f"/admin/users/{user_id}", update_data)

        return {
            "success": True,
            "message": "用户更新成功",
            "data": format_user_dict(updated_user)
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
        await call_supabase_admin_api("DELETE", f"/admin/users/{user_id}")

        return {
            "success": True,
            "message": "用户删除成功",
            "data": {"id": user_id}
        }

    except HTTPException as e:
        if "not found" in str(e.detail).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        raise
    except Exception as e:
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
        result = await call_supabase_admin_api("GET", "/admin/users")
        users = result.get("users", [])

        exists = any(u.get("email") == request.email for u in users)

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
        updated_user = await call_supabase_admin_api("PUT", f"/admin/users/{user_id}", {
            "password": request.new_password
        })

        return {
            "success": True,
            "message": "密码修改成功",
            "data": format_user_dict(updated_user)
        }

    except HTTPException as e:
        if "not found" in str(e.detail).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        raise
    except Exception as e:
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
        result = await call_supabase_admin_api("GET", f"/admin/users/{user_id}")
        existing_user = result

        # 更新 app_metadata 中的角色
        updated_user = await call_supabase_admin_api("PUT", f"/admin/users/{user_id}", {
            "app_metadata": {
                **existing_user.get("app_metadata", {}),
                "role": request.role
            }
        })

        return {
            "success": True,
            "message": "角色修改成功",
            "data": format_user_dict(updated_user)
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
        result = await call_supabase_admin_api("GET", f"/admin/users/{user_id}")
        existing_user = result
        new_banned_status = not existing_user.get("banned", False)

        # 更新用户状态
        updated_user = await call_supabase_admin_api("PUT", f"/admin/users/{user_id}", {
            "banned": new_banned_status
        })

        action = "禁用" if new_banned_status else "启用"

        return {
            "success": True,
            "message": f"用户{action}成功",
            "data": format_user_dict(updated_user)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户状态失败: {str(e)}"
        )
