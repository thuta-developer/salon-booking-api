import uuid
from datetime import datetime, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BarberWorkingHourBase(BaseModel):
    day_of_week: int = Field(
        ..., ge=0, le=6, description="0=Monday, 1=Tuesday, ..., 6=Sunday"
    )
    is_active: bool = True
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    @model_validator(mode="after")
    def validate_working_hours(self):
        if self.is_active:
            if self.start_time is None or self.end_time is None:
                raise ValueError("start_time and end_time are required when is_active is True")
            if self.start_time >= self.end_time:
                raise ValueError("start_time must be earlier than end_time")
        else:
            self.start_time = None
            self.end_time = None
        return self


class BarberWorkingHourCreate(BarberWorkingHourBase):
    pass


class BarberWorkingHourBulkUpdate(BaseModel):
    schedules: List[BarberWorkingHourCreate]


class BarberWorkingHourResponse(BarberWorkingHourBase):
    id: uuid.UUID
    shop_barber_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)