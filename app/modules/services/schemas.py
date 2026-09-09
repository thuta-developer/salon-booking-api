import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

class ServiceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Classic Men's Haircut")
    description: str = Field(None, min_length=1, max_length=255, description="Haircut includes wash, blow dry, and quick neck massage.")
    duration_minutes: int = Field(..., gt=0, description="Duration minutes")
    price: Decimal = Field(..., ge=0, description="Price")
    is_active: bool = Field(default=True)


class ServiceCreate(ServiceBase):
    category_id: uuid.UUID = Field(..., description="ID of the service category")


class ServiceUpdate(BaseModel):
    category_id: Optional[uuid.UUID] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ServiceResponse(ServiceBase):
    id: uuid.UUID
    shop_id: uuid.UUID
    category_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceCategoryBriefResponse(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class ServiceDetailResponse(ServiceResponse):
    category: Optional[ServiceCategoryBriefResponse] = None