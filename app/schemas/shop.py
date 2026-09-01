from decimal import Decimal
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from app.schemas.user import UserResponse


class ShopBase(BaseModel):
    name: str = Field(..., max_length=255, description="Shop name")
    slug: Optional[str] = Field(
        None, max_length=255, description="URL-friendly slug (auto-generated if empty)"
    )
    description: Optional[str] = Field(None, description="Shop description")
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)

    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)

    logo: Optional[str] = Field(None, max_length=500)
    cover_image: Optional[str] = Field(None, max_length=500)

    is_active: bool = True
    is_verified: bool = False


class ShopCreate(ShopBase):
    @field_validator("slug", mode="before")
    @classmethod
    def validate_slug(cls, v, info):
        if not v:
            # name ရှိမှ slug လုပ်မယ်
            name = info.data.get("name")
            if name:
                import re
                v = re.sub(r"[^\w\-]", "-", name.lower()).strip("-")
                v = re.sub(r"\-+", "-", v)
        return v


class ShopUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    logo: Optional[str] = Field(None, max_length=500)
    cover_image: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class ShopResponse(ShopBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShopDetailResponse(ShopResponse):
    owner: UserResponse   
    # services_count: Optional[int] = None  # နောက်ပိုင်း service တွေနဲ့ ချိတ်ရင် ထည့်
