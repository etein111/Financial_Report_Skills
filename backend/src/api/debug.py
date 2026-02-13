from fastapi import APIRouter

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "debug-ok"}

