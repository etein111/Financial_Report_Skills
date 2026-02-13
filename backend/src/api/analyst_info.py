from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..core.auth import get_current_user, require_admin
from ..core.config import get_settings
from ..core.supabase import get_supabase_with_user_token
from ..models.analyst import AnalystCheckEmailRequest, AnalystCreate, AnalystUpdate
from ..models.auth import CurrentUser
from ..models.common import ok

router = APIRouter(prefix="/api/analyst-info", tags=["analyst-info"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _select_clause() -> str:
    return "id,full_name,chinese_name,email,region_id,is_active,created_at,region:region_id(name)"


def _row_to_item(row: dict[str, Any]) -> dict[str, Any]:
    region = row.get("region")
    region_name = None
    if isinstance(region, dict):
        region_name = region.get("name")
    return {
        "id": row.get("id"),
        "full_name": row.get("full_name"),
        "chinese_name": row.get("chinese_name"),
        "email": row.get("email"),
        "region_id": row.get("region_id"),
        "region_name": region_name,
        "is_active": row.get("is_active", True),
        "created_at": row.get("created_at"),
    }


def list_analyst_data(access_token: str, query: str, page: int) -> dict[str, Any]:
    settings = get_settings()
    page = max(page, 1)
    page_size = settings.page_size
    start = (page - 1) * page_size
    end = start + page_size - 1
    keyword = query.strip()

    client = get_supabase_with_user_token(access_token)
    builder = client.table("analyst").select(_select_clause(), count="exact")
    if keyword:
        builder = builder.or_(
            f"full_name.ilike.%{keyword}%,chinese_name.ilike.%{keyword}%,email.ilike.%{keyword}%"
        )

    result = builder.order("created_at", desc=True).range(start, end).execute()
    return {
        "items": [_row_to_item(row) for row in (result.data or [])],
        "total": result.count or 0,
        "page": page,
        "page_size": page_size,
    }


def _email_exists(
    access_token: str,
    email: str,
    exclude_id: str | None = None,
) -> bool:
    client = get_supabase_with_user_token(access_token)
    builder = client.table("analyst").select("id", count="exact").eq("email", _normalize_email(email))
    if exclude_id:
        builder = builder.neq("id", exclude_id)
    result = builder.limit(1).execute()
    return (result.count or 0) > 0


def create_analyst_data(access_token: str, payload: AnalystCreate) -> dict[str, Any] | None:
    if _email_exists(access_token, payload.email):
        raise ValueError("Email already exists")

    client = get_supabase_with_user_token(access_token)
    body = {
        "full_name": payload.full_name.strip(),
        "chinese_name": payload.chinese_name.strip() if payload.chinese_name else None,
        "email": _normalize_email(str(payload.email)),
        "region_id": payload.region,
        "is_active": payload.is_active,
    }
    result = client.table("analyst").insert(body).execute()
    row = (result.data or [None])[0]
    return _row_to_item(row) if row else None


def update_analyst_data(
    access_token: str,
    analyst_id: str,
    payload: AnalystUpdate,
) -> dict[str, Any] | None:
    body: dict[str, Any] = {}
    if payload.full_name is not None:
        body["full_name"] = payload.full_name.strip()
    if payload.chinese_name is not None:
        body["chinese_name"] = payload.chinese_name.strip()
    if payload.email is not None:
        if _email_exists(access_token, payload.email, exclude_id=analyst_id):
            raise ValueError("Email already exists")
        body["email"] = _normalize_email(str(payload.email))
    if payload.region is not None:
        body["region_id"] = payload.region
    if payload.is_active is not None:
        body["is_active"] = payload.is_active
    if not body:
        raise ValueError("No data to update")

    client = get_supabase_with_user_token(access_token)
    result = client.table("analyst").update(body).eq("id", analyst_id).execute()
    row = (result.data or [None])[0]
    return _row_to_item(row) if row else None


def delete_analyst_data(access_token: str, analyst_id: str) -> None:
    client = get_supabase_with_user_token(access_token)
    client.table("analyst").delete().eq("id", analyst_id).execute()


def check_analyst_email_exists(access_token: str, email: str, exclude_id: str | None = None) -> bool:
    return _email_exists(access_token, email, exclude_id=exclude_id)


@router.get("")
def list_analyst(
    query: str = Query(default="", alias="q"),
    page: int = Query(default=1, ge=1),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        data = list_analyst_data(current_user.access_token, query=query, page=page)
        return ok(data=data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"List analyst info failed: {exc}",
        ) from exc


@router.post("")
def create_analyst(
    payload: AnalystCreate,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    try:
        row = create_analyst_data(current_user.access_token, payload)
        return ok(data=row, message="Analyst created")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Create analyst failed: {exc}",
        ) from exc


@router.put("/{analyst_id}")
def update_analyst(
    analyst_id: str,
    payload: AnalystUpdate,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    try:
        row = update_analyst_data(current_user.access_token, analyst_id, payload)
        return ok(data=row, message="Analyst updated")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Update analyst failed: {exc}",
        ) from exc


@router.delete("/{analyst_id}")
def delete_analyst(
    analyst_id: str,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    try:
        delete_analyst_data(current_user.access_token, analyst_id)
        return ok(message="Analyst deleted")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Delete analyst failed: {exc}",
        ) from exc


@router.post("/check-email")
def check_email(
    payload: AnalystCheckEmailRequest,
    current_user: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    exists = check_analyst_email_exists(
        current_user.access_token,
        str(payload.email),
        exclude_id=payload.exclude_id,
    )
    return ok(data={"exists": exists})
