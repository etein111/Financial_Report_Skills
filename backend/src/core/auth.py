from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status

from ..models.auth import CurrentUser
from .config import get_settings
from .supabase import get_supabase_anon

VALID_ROLES = {"admin", "sa", "analyst"}


def get_access_token(request: Request) -> str:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return token


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _normalize_role(raw_role: str | None) -> str:
    role = (raw_role or "analyst").lower()
    if role not in VALID_ROLES:
        return "analyst"
    return role


def resolve_current_user(token: str) -> CurrentUser:
    try:
        result = get_supabase_anon().auth.get_user(jwt=token)
        user = _safe_get(result, "user")
    except Exception as exc:  # pragma: no cover - 依赖外部服务
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from exc

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    app_metadata = _safe_get(user, "app_metadata", {}) or {}
    user_metadata = _safe_get(user, "user_metadata", {}) or {}
    role = _normalize_role(_safe_get(app_metadata, "role"))
    is_active = bool(_safe_get(app_metadata, "is_active", True))

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission",
        )

    return CurrentUser(
        id=str(_safe_get(user, "id", "")),
        email=str(_safe_get(user, "email", "")),
        full_name=_safe_get(user_metadata, "full_name"),
        role=role,
        is_active=is_active,
        access_token=token,
    )


def get_current_user(
    token: Annotated[str, Depends(get_access_token)],
) -> CurrentUser:
    return resolve_current_user(token)


def require_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission",
        )
    return current_user
