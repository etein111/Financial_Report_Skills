from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..core.auth import require_admin
from ..core.config import get_settings
from ..core.supabase import get_supabase_service
from ..models.auth import CurrentUser
from ..models.common import ok
from ..models.user import UserCreate, UserPasswordUpdate, UserRoleUpdate, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_users(result: Any) -> list[Any]:
    users = _safe_get(result, "users")
    if users is not None:
        return list(users)

    data = _safe_get(result, "data")
    if isinstance(data, dict) and isinstance(data.get("users"), list):
        return data["users"]
    if isinstance(result, dict) and isinstance(result.get("users"), list):
        return result["users"]
    return []


def _normalize_role(raw_role: str | None) -> str:
    role = (raw_role or "analyst").lower()
    if role not in {"admin", "sa", "analyst"}:
        return "analyst"
    return role


def _serialize_user(user: Any) -> dict[str, Any]:
    app_metadata = _safe_get(user, "app_metadata", {}) or {}
    user_metadata = _safe_get(user, "user_metadata", {}) or {}
    return {
        "id": str(_safe_get(user, "id", "")),
        "email": _safe_get(user, "email", ""),
        "full_name": _safe_get(user_metadata, "full_name"),
        "role": _normalize_role(_safe_get(app_metadata, "role")),
        "is_active": bool(_safe_get(app_metadata, "is_active", True)),
        "created_at": _safe_get(user, "created_at"),
    }


def _admin() -> Any:
    return get_supabase_service().auth.admin


def _admin_list_users(page: int, per_page: int) -> list[Any]:
    admin = _admin()
    result = admin.list_users(page=page, per_page=per_page)
    return _extract_users(result)


def _admin_get_user(user_id: str) -> Any | None:
    admin = _admin()
    if hasattr(admin, "get_user_by_id"):
        result = admin.get_user_by_id(user_id)
        user = _safe_get(result, "user")
        if user:
            return user
    for user in _fetch_all_user_objects():
        if str(_safe_get(user, "id", "")) == user_id:
            return user
    return None


def _admin_create_user(payload: dict[str, Any]) -> Any:
    admin = _admin()
    return admin.create_user(payload)


def _admin_update_user(user_id: str, payload: dict[str, Any]) -> Any:
    admin = _admin()
    if hasattr(admin, "update_user_by_id"):
        return admin.update_user_by_id(user_id, payload)
    if hasattr(admin, "update_user"):
        return admin.update_user(user_id, payload)
    raise RuntimeError("Supabase admin SDK 不支持 update_user")


def _admin_delete_user(user_id: str) -> Any:
    admin = _admin()
    return admin.delete_user(user_id)


def _fetch_all_user_objects() -> list[Any]:
    all_users: list[Any] = []
    page = 1
    per_page = 200
    while page <= 50:
        batch = _admin_list_users(page=page, per_page=per_page)
        all_users.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return all_users


def _fetch_all_users() -> list[dict[str, Any]]:
    return [_serialize_user(user) for user in _fetch_all_user_objects()]


def _sort_created_desc(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key_fn(item: dict[str, Any]) -> tuple[int, str]:
        raw = item.get("created_at")
        if not raw:
            return (0, "")
        if isinstance(raw, datetime):
            return (1, raw.isoformat())
        return (1, str(raw))

    return sorted(items, key=key_fn, reverse=True)


def list_users_data(query: str, page: int) -> dict[str, Any]:
    settings = get_settings()
    all_users = _fetch_all_users()
    keyword = query.strip().lower()
    if keyword:
        all_users = [
            item
            for item in all_users
            if keyword in (item.get("email") or "").lower()
            or keyword in (item.get("full_name") or "").lower()
        ]

    ordered = _sort_created_desc(all_users)
    total = len(ordered)
    page = max(page, 1)
    page_size = settings.page_size
    start = (page - 1) * page_size
    end = start + page_size
    items = ordered[start:end]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def create_user_data(payload: UserCreate) -> dict[str, Any]:
    role = _normalize_role(payload.role)
    body = {
        "email": str(payload.email),
        "password": payload.password,
        "email_confirm": True,
        "user_metadata": {"full_name": payload.full_name},
        "app_metadata": {"role": role, "is_active": True},
    }
    created = _admin_create_user(body)
    created_user = _safe_get(created, "user") or created
    return _serialize_user(created_user)


def update_user_data(user_id: str, payload: UserUpdate) -> dict[str, Any]:
    existing = _admin_get_user(user_id)
    if not existing:
        raise LookupError("User not found")

    app_metadata = _safe_get(existing, "app_metadata", {}) or {}
    user_metadata = _safe_get(existing, "user_metadata", {}) or {}
    if payload.full_name is not None:
        user_metadata["full_name"] = payload.full_name

    body: dict[str, Any] = {
        "app_metadata": {
            "role": _normalize_role(_safe_get(app_metadata, "role")),
            "is_active": bool(_safe_get(app_metadata, "is_active", True)),
        },
        "user_metadata": user_metadata,
    }
    if payload.email:
        body["email"] = str(payload.email)

    updated = _admin_update_user(user_id, body)
    updated_user = _safe_get(updated, "user") or updated
    return _serialize_user(updated_user)


def update_user_password_data(user_id: str, payload: UserPasswordUpdate) -> None:
    _admin_update_user(user_id, {"password": payload.password})


def update_user_role_data(user_id: str, payload: UserRoleUpdate) -> dict[str, Any]:
    existing = _admin_get_user(user_id)
    if not existing:
        raise LookupError("User not found")

    app_metadata = _safe_get(existing, "app_metadata", {}) or {}
    body = {
        "app_metadata": {
            "role": _normalize_role(payload.role),
            "is_active": bool(_safe_get(app_metadata, "is_active", True)),
        }
    }
    updated = _admin_update_user(user_id, body)
    updated_user = _safe_get(updated, "user") or updated
    return _serialize_user(updated_user)


def toggle_user_status_data(user_id: str) -> dict[str, Any]:
    existing = _admin_get_user(user_id)
    if not existing:
        raise LookupError("User not found")

    app_metadata = _safe_get(existing, "app_metadata", {}) or {}
    role = _normalize_role(_safe_get(app_metadata, "role"))
    current_active = bool(_safe_get(app_metadata, "is_active", True))
    next_active = not current_active
    _admin_update_user(
        user_id,
        {"app_metadata": {"role": role, "is_active": next_active}},
    )
    return {"id": user_id, "is_active": next_active}


def delete_user_data(user_id: str) -> None:
    _admin_delete_user(user_id)


@router.get("")
def list_users(
    query: str = Query(default="", alias="q"),
    page: int = Query(default=1, ge=1),
    _: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    try:
        data = list_users_data(query=query, page=page)
        return ok(data=data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"List users failed: {exc}",
        ) from exc


@router.post("")
def create_user(payload: UserCreate, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    try:
        data = create_user_data(payload)
        return ok(data=data, message="User created")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Create user failed: {exc}",
        ) from exc


@router.put("/{user_id}")
def update_user(
    user_id: str,
    payload: UserUpdate,
    _: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    try:
        data = update_user_data(user_id, payload)
        return ok(data=data, message="User updated")
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Update user failed: {exc}",
        ) from exc


@router.put("/{user_id}/password")
def update_password(
    user_id: str,
    payload: UserPasswordUpdate,
    _: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    try:
        update_user_password_data(user_id, payload)
        return ok(message="Password updated")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Update password failed: {exc}",
        ) from exc


@router.put("/{user_id}/role")
def update_role(
    user_id: str,
    payload: UserRoleUpdate,
    _: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    try:
        data = update_user_role_data(user_id, payload)
        return ok(data=data, message="Role updated")
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Update role failed: {exc}",
        ) from exc


@router.put("/{user_id}/toggle-status")
def toggle_status(user_id: str, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    try:
        data = toggle_user_status_data(user_id)
        return ok(data=data, message="Status updated")
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Toggle status failed: {exc}",
        ) from exc


@router.delete("/{user_id}")
def delete_user(user_id: str, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    try:
        delete_user_data(user_id)
        return ok(message="User deleted")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Delete user failed: {exc}",
        ) from exc

