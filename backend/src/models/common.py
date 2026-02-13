from typing import Any


def ok(data: Any = None, message: str = "OK") -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def fail(message: str, error: str) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "error": error,
    }

