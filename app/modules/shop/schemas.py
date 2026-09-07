"""Shop module Pydantic schemas — Shop.
"""
import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.users.schemas import UserResponse

# ==========================================
# SHOP SCHEMAS
# ==========================================
class ShopBase(BaseModel):
    name: str = Field(..., max_length=255, description="Shop name")
    slug: Optional[str] = Field(
        None,
        max_length=255,
        description="URL-friendly slug (auto-generated if empty)",
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


class ShopCreate(ShopBase):
    pass


class ShopOwnerUpdate(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)


class ShopAdminStatusUpdate(BaseModel):
    is_active: Optional[bool] = None

class ShopAdminVerificationUpdate(BaseModel):
    is_verified: Optional[bool] = None

class ShopResponse(ShopBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShopDetailResponse(ShopResponse):
    owner: UserResponse