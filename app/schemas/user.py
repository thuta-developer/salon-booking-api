import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from app.schemas.rbac import RoleResponse


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
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return _validate_password(v)


class UserWithRolesResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
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