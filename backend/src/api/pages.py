from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from ..core.auth import get_current_user, require_admin, resolve_current_user
from ..core.config import get_settings
from ..models.analyst import AnalystCreate, AnalystUpdate
from ..models.auth import CurrentUser
from ..models.region import RegionCreate, RegionUpdate
from ..models.user import UserCreate, UserRoleUpdate, UserUpdate
from .analyst_info import create_analyst_data, delete_analyst_data, list_analyst_data, update_analyst_data
from .regions import (
    create_region_data,
    delete_region_data,
    list_region_options,
    list_regions_data,
    update_region_data,
)
from .users import (
    create_user_data,
    delete_user_data,
    list_users_data,
    toggle_user_status_data,
    update_user_data,
    update_user_role_data,
)

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

UTC8 = timezone(timedelta(hours=8))


def _format_utc8(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return value
    else:
        return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(UTC8).strftime("%Y-%m-%d %H:%M:%S")


templates.env.filters["utc8"] = _format_utc8


def _get_current_user_optional(request: Request) -> CurrentUser | None:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    try:
        return resolve_current_user(token)
    except Exception:
        return None


def _safe_page(value: int | str) -> int:
    try:
        page = int(value)
    except (TypeError, ValueError):
        return 1
    return max(page, 1)


def _to_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "on", "yes"}


def _render(
    request: Request,
    template: str,
    context: dict[str, Any],
    status_code: int = 200,
) -> HTMLResponse:
    payload = {"request": request, **context}
    return templates.TemplateResponse(request, template, payload, status_code=status_code)


def _users_context(current_user: CurrentUser, q: str, page: int, message: str = "", error: str = "") -> dict[str, Any]:
    data = list_users_data(query=q, page=page)
    return {
        "current_user": current_user,
        "items": data["items"],
        "total": data["total"],
        "page": data["page"],
        "page_size": data["page_size"],
        "query": q,
        "message": message,
        "error": error,
    }


def _regions_context(current_user: CurrentUser, q: str, page: int, message: str = "", error: str = "") -> dict[str, Any]:
    data = list_regions_data(current_user.access_token, query=q, page=page)
    return {
        "current_user": current_user,
        "items": data["items"],
        "total": data["total"],
        "page": data["page"],
        "page_size": data["page_size"],
        "query": q,
        "message": message,
        "error": error,
    }


def _analyst_context(current_user: CurrentUser, q: str, page: int, message: str = "", error: str = "") -> dict[str, Any]:
    data = list_analyst_data(current_user.access_token, query=q, page=page)
    return {
        "current_user": current_user,
        "items": data["items"],
        "total": data["total"],
        "page": data["page"],
        "page_size": data["page_size"],
        "query": q,
        "regions_options": list_region_options(current_user.access_token),
        "message": message,
        "error": error,
    }


@router.get("/", response_class=HTMLResponse)
def home() -> RedirectResponse:
    return RedirectResponse("/login", status_code=302)


@router.get("/login", response_class=HTMLResponse, response_model=None)
def login_page(request: Request) -> Response:
    current_user = _get_current_user_optional(request)
    if current_user:
        return RedirectResponse("/desktop", status_code=302)
    return _render(request, "login.html", {"title": "Login"})


@router.get("/desktop", response_class=HTMLResponse)
def desktop_page(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> HTMLResponse:
    return _render(
        request,
        "desktop.html",
        {
            "title": "Desktop",
            "current_user": current_user,
        },
    )


@router.get("/403", response_class=HTMLResponse)
def forbidden_page(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> HTMLResponse:
    return _render(
        request,
        "403.html",
        {"title": "Forbidden", "current_user": current_user},
        status_code=403,
    )


@router.get("/users", response_class=HTMLResponse)
def users_page(
    request: Request,
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    return _render(
        request,
        "users/index.html",
        {"title": "Users", "current_user": current_user},
    )


@router.get("/users/table", response_class=HTMLResponse)
def users_table_partial(
    request: Request,
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    return _render(request, "users/_table.html", _users_context(current_user, q, page))


@router.post("/users/actions/create", response_class=HTMLResponse)
def users_create_action(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form("analyst"),
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        create_user_data(UserCreate(email=email, full_name=full_name, password=password, role=role))
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, message="User created"),
        )
    except Exception as exc:
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, error=str(exc)),
        )


@router.post("/users/actions/{user_id}/update", response_class=HTMLResponse)
def users_update_action(
    user_id: str,
    request: Request,
    email: str = Form(...),
    full_name: str = Form(""),
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        update_user_data(user_id, UserUpdate(email=email, full_name=full_name or None))
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, message="User updated"),
        )
    except Exception as exc:
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, error=str(exc)),
        )


@router.post("/users/actions/{user_id}/role", response_class=HTMLResponse)
def users_role_action(
    user_id: str,
    request: Request,
    role: str = Form(...),
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        update_user_role_data(user_id, UserRoleUpdate(role=role))
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, message="Role updated"),
        )
    except Exception as exc:
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, error=str(exc)),
        )


@router.post("/users/actions/{user_id}/toggle-status", response_class=HTMLResponse)
def users_toggle_action(
    user_id: str,
    request: Request,
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        toggle_user_status_data(user_id)
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, message="Status updated"),
        )
    except Exception as exc:
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, error=str(exc)),
        )


@router.post("/users/actions/{user_id}/delete", response_class=HTMLResponse)
def users_delete_action(
    user_id: str,
    request: Request,
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        delete_user_data(user_id)
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, message="User deleted"),
        )
    except Exception as exc:
        return _render(
            request,
            "users/_table.html",
            _users_context(current_user, q, safe_page, error=str(exc)),
        )


@router.get("/regions", response_class=HTMLResponse)
def regions_page(
    request: Request,
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    return _render(
        request,
        "regions/index.html",
        {"title": "Regions", "current_user": current_user},
    )


@router.get("/regions/table", response_class=HTMLResponse)
def regions_table_partial(
    request: Request,
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    return _render(request, "regions/_table.html", _regions_context(current_user, q, page))


@router.post("/regions/actions/create", response_class=HTMLResponse)
def regions_create_action(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        create_region_data(current_user.access_token, RegionCreate(name=name, code=code))
        return _render(
            request,
            "regions/_table.html",
            _regions_context(current_user, q, safe_page, message="Region created"),
        )
    except Exception as exc:
        return _render(
            request,
            "regions/_table.html",
            _regions_context(current_user, q, safe_page, error=str(exc)),
        )


@router.post("/regions/actions/{region_id}/update", response_class=HTMLResponse)
def regions_update_action(
    region_id: str,
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        update_region_data(current_user.access_token, region_id, RegionUpdate(name=name, code=code))
        return _render(
            request,
            "regions/_table.html",
            _regions_context(current_user, q, safe_page, message="Region updated"),
        )
    except Exception as exc:
        return _render(
            request,
            "regions/_table.html",
            _regions_context(current_user, q, safe_page, error=str(exc)),
        )


@router.post("/regions/actions/{region_id}/delete", response_class=HTMLResponse)
def regions_delete_action(
    region_id: str,
    request: Request,
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        delete_region_data(current_user.access_token, region_id)
        return _render(
            request,
            "regions/_table.html",
            _regions_context(current_user, q, safe_page, message="Region deleted"),
        )
    except Exception as exc:
        return _render(
            request,
            "regions/_table.html",
            _regions_context(current_user, q, safe_page, error=str(exc)),
        )


@router.get("/analyst-info", response_class=HTMLResponse)
def analyst_info_page(
    request: Request,
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    return _render(
        request,
        "analyst_info/index.html",
        {"title": "Analyst Info", "current_user": current_user},
    )


@router.get("/analyst-info/table", response_class=HTMLResponse)
def analyst_info_table_partial(
    request: Request,
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    return _render(request, "analyst_info/_table.html", _analyst_context(current_user, q, page))


@router.post("/analyst-info/actions/create", response_class=HTMLResponse)
def analyst_create_action(
    request: Request,
    full_name: str = Form(...),
    chinese_name: str = Form(""),
    email: str = Form(...),
    region: str = Form(...),
    is_active: str = Form("true"),
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        create_analyst_data(
            current_user.access_token,
            AnalystCreate(
                full_name=full_name,
                chinese_name=chinese_name or None,
                email=email,
                region=region,
                is_active=_to_bool(is_active),
            ),
        )
        return _render(
            request,
            "analyst_info/_table.html",
            _analyst_context(current_user, q, safe_page, message="Analyst created"),
        )
    except Exception as exc:
        return _render(
            request,
            "analyst_info/_table.html",
            _analyst_context(current_user, q, safe_page, error=str(exc)),
        )


@router.post("/analyst-info/actions/{analyst_id}/update", response_class=HTMLResponse)
def analyst_update_action(
    analyst_id: str,
    request: Request,
    full_name: str = Form(...),
    chinese_name: str = Form(""),
    email: str = Form(...),
    region: str = Form(...),
    is_active: str = Form("true"),
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        update_analyst_data(
            current_user.access_token,
            analyst_id,
            AnalystUpdate(
                full_name=full_name,
                chinese_name=chinese_name or None,
                email=email,
                region=region,
                is_active=_to_bool(is_active),
            ),
        )
        return _render(
            request,
            "analyst_info/_table.html",
            _analyst_context(current_user, q, safe_page, message="Analyst updated"),
        )
    except Exception as exc:
        return _render(
            request,
            "analyst_info/_table.html",
            _analyst_context(current_user, q, safe_page, error=str(exc)),
        )


@router.post("/analyst-info/actions/{analyst_id}/delete", response_class=HTMLResponse)
def analyst_delete_action(
    analyst_id: str,
    request: Request,
    q: str = Form(""),
    page: int = Form(1),
    current_user: CurrentUser = Depends(require_admin),
) -> HTMLResponse:
    safe_page = _safe_page(page)
    try:
        delete_analyst_data(current_user.access_token, analyst_id)
        return _render(
            request,
            "analyst_info/_table.html",
            _analyst_context(current_user, q, safe_page, message="Analyst deleted"),
        )
    except Exception as exc:
        return _render(
            request,
            "analyst_info/_table.html",
            _analyst_context(current_user, q, safe_page, error=str(exc)),
        )
