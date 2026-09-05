"""Standardized API response envelope helpers."""
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Generic envelope: `{"success": true, "message": "...", "data": ...}`."""

    success: bool = True
    message: str = "OK"
    data: Optional[T] = None


def success_response(
    data: Any = None,
    message: str = "Success",
    *,
    success: bool = True,
) -> dict:
    return {
        "success": success,
        "message": message,
        "data": data,
    }


def error_response(
    message: str = "Error",
    data: Any = None,
    *,
    success: bool = False,
) -> dict:
    return {
        "success": success,
        "message": message,
        "data": data,
    }


def item_id_list(items: List[Any]) -> List[str]:
    """Extract string ids from a list of objects/uuids (useful for scripts)."""
    return [str(getattr(i, "id", i)) for i in items]