"""Users module Pydantic schemas — User + Shop.

``UserResponse.roles`` returns a list of role names, while
``UserWithRolesResponse.roles`` returns full ``RoleResponse`` objects.
"""
import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.auth.schemas import RoleResponse


# ==========================================
# USER SCHEMAS
# ==========================================
PASSWORD_MIN_LENGTH = 8
# bcrypt ၏ Maximum Input Length (72 bytes) — ထက်ပိုကြီးသော password ကို ခွင့်မပြုပါ
PASSWORD_MAX_LENGTH = 72


def _validate_password(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
        )
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must not exceed {PASSWORD_MAX_LENGTH} characters"
        )
    return value


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    account_type: str = "customer"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        # Duplicate accounts (case-difference) မဖြစ်စေရန် normalize လုပ်သည်
        return v.strip().lower()


class UserCreate(UserBase):
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str) -> str:
        return _validate_password(v)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    account_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserWithRolesResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    account_type: str
    is_active: bool
    is_superuser: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

    roles: List[RoleResponse] = []


class UserResponse(UserBase):
    id: uuid.UUID
    is_superuser: bool
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    roles: List[str] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator("roles", mode="before")
    @classmethod
    def extract_role_names(cls, v: Any) -> List[str]:
        if not v:
            return []

        # SQLAlchemy Relationship မှ Object list ဝင်လာပါက role.name များကို သီးသန့်ထုတ်ယူမည်
        result = []
        for role in v:
            if isinstance(role, str):
                result.append(role)
            elif hasattr(role, "name"):
                result.append(role.name)
        return result


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
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShopDetailResponse(ShopResponse):
    owner: UserResponse