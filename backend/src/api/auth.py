from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ..core.auth import get_current_user
from ..core.config import get_settings
from ..core.supabase import get_supabase_anon
from ..models.auth import CurrentUser, ForgotPasswordRequest, LoginRequest
from ..models.common import ok

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _normalize_role(raw_role: str | None) -> str:
    role = (raw_role or "analyst").lower()
    if role not in {"admin", "sa", "analyst"}:
        return "analyst"
    return role


@router.post("/login")
def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    settings = get_settings()
    try:
        result = get_supabase_anon().auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception as exc:  # pragma: no cover - 依赖外部服务
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    session = _safe_get(result, "session")
    user = _safe_get(result, "user")
    access_token = _safe_get(session, "access_token")
    if not access_token or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
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

    response.set_cookie(
        key=settings.session_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_cookie_max_age,
        path="/",
    )
    return ok(
        data={
            "id": str(_safe_get(user, "id", "")),
            "email": _safe_get(user, "email", ""),
            "full_name": _safe_get(user_metadata, "full_name"),
            "role": role,
            "is_active": is_active,
        },
        message="Login success",
    )


@router.post("/logout")
def logout(response: Response) -> dict[str, Any]:
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return ok(message="Logout success")


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    return ok(
        data={
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active,
        }
    )


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict[str, Any]:
    settings = get_settings()
    auth_client = get_supabase_anon().auth
    redirect_to = settings.supabase_password_reset_redirect
    options = {"redirect_to": redirect_to} if redirect_to else {}

    # 统一返回成功文案，避免邮箱枚举。
    try:  # pragma: no cover - 依赖外部服务
        if hasattr(auth_client, "reset_password_email"):
            auth_client.reset_password_email(payload.email, options)
        elif hasattr(auth_client, "reset_password_for_email"):
            auth_client.reset_password_for_email(payload.email, options)
    except Exception:
        pass

    return ok(message="If the account exists, a reset email has been sent")

