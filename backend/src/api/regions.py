"""
Region 管理 API

处理地区数据的 CRUD 操作
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Optional
from ..models.region import RegionCreate, RegionUpdate, RegionResponse
from ..core.security import get_current_user, require_admin
from ..core.supabase import get_supabase

router = APIRouter()
supabase = get_supabase()


@router.get("", response_model=list[RegionResponse])
async def list_regions(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> list:
    """
    获取地区列表

    所有认证用户都可以查看地区列表。
    """
    try:
        result = supabase.table("region").select("*").order("name").execute()

        return result.data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取地区列表失败: {str(e)}"
        )


@router.post("", response_model=RegionResponse)
async def create_region(
    region_data: RegionCreate,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    创建新地区

    只有 Admin 可以创建地区。
    """
    try:
        # 检查代码是否已存在
        existing = supabase.table("region").select("*").eq("code", region_data.code).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"地区代码 '{region_data.code}' 已存在"
            )

        # 检查名称是否已存在
        existing = supabase.table("region").select("*").eq("name", region_data.name).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"地区名称 '{region_data.name}' 已存在"
            )

        # 创建地区
        result = supabase.table("region").insert({
            "name": region_data.name,
            "code": region_data.code
        }).execute()

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建地区失败: {str(e)}"
        )


@router.put("/{region_id}", response_model=RegionResponse)
async def update_region(
    region_id: str,
    region_data: RegionUpdate,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    更新地区信息

    只有 Admin 可以更新地区信息。
    """
    try:
        # 准备更新数据
        update_data = {}
        if region_data.name is not None:
            update_data["name"] = region_data.name
        if region_data.code is not None:
            update_data["code"] = region_data.code

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供需要更新的数据"
            )

        # 检查名称/代码是否与其他地区冲突
        if region_data.name is not None:
            existing = supabase.table("region").select("*").eq("name", region_data.name).execute()
            if existing.data and any(r["id"] != region_id for r in existing.data):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"地区名称 '{region_data.name}' 已被其他地区使用"
                )

        if region_data.code is not None:
            existing = supabase.table("region").select("*").eq("code", region_data.code).execute()
            if existing.data and any(r["id"] != region_id for r in existing.data):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"地区代码 '{region_data.code}' 已被其他地区使用"
                )

        # 更新地区
        result = supabase.table("region").update(update_data).eq("id", region_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="地区不存在"
            )

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新地区失败: {str(e)}"
        )


@router.delete("/{region_id}")
async def delete_region(
    region_id: str,
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    """
    删除地区

    只有 Admin 可以删除地区。
    """
    try:
        # 先检查地区是否存在
        existing = supabase.table("region").select("*").eq("id", region_id).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="地区不存在"
            )

        # 检查是否有关联的 Analyst
        analysts = supabase.table("analyst").select("*").eq("region_id", region_id).execute()
        if analysts.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"无法删除：仍有 {len(analysts.data)} 个 Analyst 关联到此地区"
            )

        # 删除地区
        supabase.table("region").delete().eq("id", region_id).execute()

        return {
            "success": True,
            "message": "地区删除成功",
            "data": {"id": region_id}
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除地区失败: {str(e)}"
        )
