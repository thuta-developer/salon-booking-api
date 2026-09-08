import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

class ServiceCategoryBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Category name",
        example="Haircuts",
    )
    description: Optional[str] = Field(
        None,
        description="Category description",
        example="All types of hair cutting and styling services",
    )
    display_order: int = Field(
        default=0,
        ge=0,
        description="Sort order for the category within this shop",
        example=1,
    )
    is_active: bool = Field(default=True, description="Whether the category is active")


class ServiceCategoryCreate(ServiceCategoryBase):
    pass


class ServiceCategoryUpdate(BaseModel):
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Category name",
        example="Haircuts & Styling",
    )
    description: Optional[str] = None
    display_order: Optional[int] = Field(
        None, ge=0, description="Sort order for the category within this shop"
    )
    is_active: Optional[bool] = None


class ServiceCategoryResponse(ServiceCategoryBase):
    id: uuid.UUID
    shop_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryReorderItem(BaseModel):
    id: uuid.UUID
    display_order: int = Field(..., ge=0)