from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..core.auth import get_current_user, require_admin
from ..core.config import get_settings
from ..core.supabase import get_supabase_with_user_token
from ..models.auth import CurrentUser
from ..models.common import ok
from ..models.region import RegionCreate, RegionUpdate

router = APIRouter(prefix="/api/regions", tags=["regions"])


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def list_regions_data(access_token: str, query: str, page: int) -> dict[str, Any]:
    settings = get_settings()
    page = max(page, 1)
    page_size = settings.page_size
    start = (page - 1) * page_size
    end = start + page_size - 1
    keyword = query.strip()

    client = get_supabase_with_user_token(access_token)
    builder = client.table("region").select("*", count="exact")
    if keyword:
        builder = builder.or_(f"name.ilike.%{keyword}%,code.ilike.%{keyword}%")
    result = builder.order("created_at", desc=True).range(start, end).execute()
    return {
        "items": result.data or [],
        "total": result.count or 0,
        "page": page,
        "page_size": page_size,
    }


def list_region_options(access_token: str) -> list[dict[str, Any]]:
    client = get_supabase_with_user_token(access_token)
    result = client.table("region").select("id,name").order("name", desc=False).execute()
    return result.data or []


def create_region_data(access_token: str, payload: RegionCreate) -> dict[str, Any]:
    client = get_supabase_with_user_token(access_token)
    body = {"name": payload.name.strip(), "code": payload.code.strip()}
    result = client.table("region").insert(body).execute()
    return (result.data or [None])[0]


def update_region_data(access_token: str, region_id: str, payload: RegionUpdate) -> dict[str, Any] | None:
    client = get_supabase_with_user_token(access_token)
    body: dict[str, Any] = {}
    if payload.name is not None:
        body["name"] = payload.name.strip()
    if payload.code is not None:
        body["code"] = payload.code.strip()
    if not body:
        raise ValueError("No data to update")
    result = client.table("region").update(body).eq("id", region_id).execute()
    return (result.data or [None])[0]


def delete_region_data(access_token: str, region_id: str) -> None:
    client = get_supabase_with_user_token(access_token)
    client.table("region").delete().eq("id", region_id).execute()


@router.get("")
def list_regions(
    query: str = Query(default="", alias="q"),
    page: int = Query(default=1, ge=1),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        data = list_regions_data(current_user.access_token, query=query, page=page)
        return ok(data=data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"List regions failed: {exc}",
        ) from exc


@router.post("")
def create_region(
    payload: RegionCreate,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    try:
        row = create_region_data(current_user.access_token, payload)
        return ok(data=row, message="Region created")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Create region failed: {exc}",
        ) from exc


@router.put("/{region_id}")
def update_region(
    region_id: str,
    payload: RegionUpdate,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    try:
        row = update_region_data(current_user.access_token, region_id, payload)
        return ok(data=row, message="Region updated")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Update region failed: {exc}",
        ) from exc


@router.delete("/{region_id}")
def delete_region(region_id: str, current_user: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    try:
        delete_region_data(current_user.access_token, region_id)
        return ok(message="Region deleted")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Delete region failed: {exc}",
        ) from exc
