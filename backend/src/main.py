from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .api import analyst_info, auth, pages, regions, users
from .api.debug import router as debug_router
from .core.config import get_settings

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Neolyst Auth And User Management")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(regions.router)
app.include_router(analyst_info.router)

settings = get_settings()
if settings.debug and not settings.is_production:
    app.include_router(debug_router)


def _is_api_request(path: str) -> bool:
    return path.startswith("/api/")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if _is_api_request(request.url.path):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    if exc.status_code == 401:
        return RedirectResponse("/login", status_code=302)
    if exc.status_code == 403:
        return templates.TemplateResponse(
            request,
            "403.html",
            {"request": request, "title": "Forbidden", "message": "No permission"},
            status_code=403,
        )
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "env": settings.app_env,
    }
