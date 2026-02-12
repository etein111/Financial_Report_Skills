"""
Analyst 信息管理 API

处理 Analyst 信息的 CRUD 操作
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated, Optional
from ..models.analyst import (
    AnalystCreate, AnalystUpdate, AnalystResponse,
    CheckEmailRequest, CheckEmailResponse
)
from ..core.security import get_current_user, require_admin
from ..core.supabase import get_supabase

router = APIRouter()
supabase = get_supabase()


@router.get("/test-insert")
async def test_insert_direct(
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """直接测试 Supabase 插入"""
    try:
        import base64
        import json

        # 解码当前使用的 key
        key_parts = supabase.supabase_key.split('.')
        if len(key_parts) >= 2:
            payload = key_parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.b64decode(payload)
            key_info = json.loads(decoded)
            print(f"DEBUG: Using key with role: {key_info.get('role')}")

        # 尝试插入
        result = supabase.table('analyst').insert({
            'full_name': 'API Test Insert',
            'email': f'api_test_{id(result)}@test.com'
        }).execute()

        return {
            "success": True,
            "key_role": key_info.get('role'),
            "result": result.data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@router.get("", response_model=list[AnalystResponse])
async def list_analysts(
    current_user: Annotated[dict, Depends(get_current_user)],
    search: Optional[str] = Query(None, description="按姓名或邮箱搜索"),
    is_active: Optional[bool] = Query(None, description="过滤激活状态")
) -> list:
    """
    获取 Analyst 信息列表

    所有认证用户都可以查看 Analyst 信息列表。
    支持按姓名或邮箱搜索，以及按激活状态过滤。
    """
    try:
        query = supabase.table("analyst").select("*, region(*)")

        # 应用过滤
        if search:
            search_lower = search.lower()
            # 使用 or 条件搜索 full_name 和 email
            query = query.or_(f"full_name.ilike.%{search_lower}%,email.ilike.%{search_lower}%")

        if is_active is not None:
            query = query.eq("is_active", is_active)

        result = query.order("full_name").execute()

        return result.data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 Analyst 信息列表失败: {str(e)}"
        )


@router.post("", response_model=AnalystResponse)
async def create_analyst(
    analyst_data: AnalystCreate,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    创建新 Analyst 信息

    只有 Admin 可以创建 Analyst 信息。
    """
    try:
        # 检查邮箱是否已存在
        existing = supabase.table("analyst").select("*").eq("email", analyst_data.email).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"邮箱 '{analyst_data.email}' 已被使用"
            )

        # 准备创建数据
        insert_data = {
            "full_name": analyst_data.full_name,
            "email": analyst_data.email
        }

        if analyst_data.chinese_name is not None:
            insert_data["chinese_name"] = analyst_data.chinese_name
        if analyst_data.suffix is not None:
            insert_data["suffix"] = analyst_data.suffix
        if analyst_data.region_id is not None:
            insert_data["region_id"] = str(analyst_data.region_id)
        if analyst_data.sfc is not None:
            insert_data["sfc"] = analyst_data.sfc

        # 创建 Analyst 信息
        insert_result = supabase.table("analyst").insert(insert_data).execute()

        # 获取完整的 Analyst 信息（包含关联的 Region）
        result = supabase.table("analyst").select("*, region(*)").eq("id", insert_result.data[0]["id"]).execute()

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建 Analyst 信息失败: {str(e)}"
        )


@router.put("/{analyst_id}", response_model=AnalystResponse)
async def update_analyst(
    analyst_id: str,
    analyst_data: AnalystUpdate,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    更新 Analyst 信息

    只有 Admin 可以更新 Analyst 信息。
    """
    try:
        # 检查 Analyst 是否存在
        existing = supabase.table("analyst").select("*").eq("id", analyst_id).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analyst 信息不存在"
            )

        # 准备更新数据
        update_data = {}
        if analyst_data.full_name is not None:
            update_data["full_name"] = analyst_data.full_name
        if analyst_data.chinese_name is not None:
            update_data["chinese_name"] = analyst_data.chinese_name
        if analyst_data.email is not None:
            # 检查邮箱是否与其他 Analyst 冲突
            email_check = supabase.table("analyst").select("*").eq("email", analyst_data.email).execute()
            if email_check.data and any(a["id"] != analyst_id for a in email_check.data):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"邮箱 '{analyst_data.email}' 已被其他 Analyst 使用"
                )
            update_data["email"] = analyst_data.email
        if analyst_data.suffix is not None:
            update_data["suffix"] = analyst_data.suffix
        if analyst_data.region_id is not None:
            update_data["region_id"] = str(analyst_data.region_id)
        if analyst_data.sfc is not None:
            update_data["sfc"] = analyst_data.sfc
        if analyst_data.is_active is not None:
            update_data["is_active"] = analyst_data.is_active

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供需要更新的数据"
            )

        # 更新 Analyst 信息
        update_result = supabase.table("analyst").update(update_data).eq("id", analyst_id).execute()

        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analyst 信息不存在"
            )

        # 获取完整的 Analyst 信息（包含关联的 Region）
        result = supabase.table("analyst").select("*, region(*)").eq("id", analyst_id).execute()

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新 Analyst 信息失败: {str(e)}"
        )


@router.delete("/{analyst_id}")
async def delete_analyst(
    analyst_id: str,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    删除 Analyst 信息

    只有 Admin 可以删除 Analyst 信息。
    """
    try:
        # 检查 Analyst 是否存在
        existing = supabase.table("analyst").select("*").eq("id", analyst_id).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analyst 信息不存在"
            )

        # 删除 Analyst 信息
        supabase.table("analyst").delete().eq("id", analyst_id).execute()

        return {
            "success": True,
            "message": "Analyst 信息删除成功",
            "data": {"id": analyst_id}
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除 Analyst 信息失败: {str(e)}"
        )


@router.post("/check-email", response_model=CheckEmailResponse)
async def check_email(
    request: CheckEmailRequest,
    current_user: Annotated[dict, Depends(require_admin)]
) -> CheckEmailResponse:
    """
    检查邮箱是否已被使用

    用于前端实时验证邮箱唯一性。
    """
    try:
        result = supabase.table("analyst").select("*").eq("email", request.email).execute()
        exists = len(result.data) > 0

        return CheckEmailResponse(exists=exists)

    except Exception:
        # 出错时返回 False 以避免阻止正常操作
        return CheckEmailResponse(exists=False)
