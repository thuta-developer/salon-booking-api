"""Pagination primitives shared across modules."""
import math
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    total_pages: int


def build_paginated_response(
    items: List[T],
    total: int,
    page: int,
    size: int,
) -> PaginatedResponse[T]:
    """Build a :class:`PaginatedResponse` computing total_pages automatically."""
    total_pages = math.ceil(total / size) if total > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )