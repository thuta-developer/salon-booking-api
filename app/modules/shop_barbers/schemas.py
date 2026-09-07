import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class BarberUserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ShopBarberBase(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=255, example="Barber Alex")
    bio: Optional[str] = Field(None, example="Experienced in modern fades and beard grooming")
    is_active: bool = True

class ShopBarberCreate(ShopBarberBase):
    barber_id: uuid.UUID = Field(..., description="User ID of the barber")
    joined_at: Optional[datetime] = None

class ShopBarberUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=255)
    bio: Optional[str] = None
    is_active: Optional[bool] = None


class ShopBarberResponse(ShopBarberBase):
    id: uuid.UUID
    shop_id: uuid.UUID
    barber_id: uuid.UUID
    joined_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    barber: Optional[BarberUserResponse] = None

    model_config = ConfigDict(from_attributes=True)