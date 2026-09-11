import uuid
from datetime import datetime, time
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class BusinessHourBase(BaseModel):
    day_of_week: int = Field(
        ..., ge=0, le=6, description="0: Monday, 1: Tuesday, ..., 6: Sunday"
    )
    is_closed: bool = False
    open_time: Optional[time] = Field(None, example="09:00:00")
    close_time: Optional[time] = Field(None, example="18:00:00")

    @model_validator(mode="after")
    def validate_times(self) -> "BusinessHourBase":
        """ဆိုင်ဖွင့်ထားပါက open_time နှင့် close_time မဖြစ်မနေ ပါဝင်ရမည်ဖြစ်ပြီး၊ ဆိုင်ပိတ်ပါက Null ဖြစ်ရမည်။"""
        if not self.is_closed:
            if self.open_time is None or self.close_time is None:
                raise ValueError("open_time and close_time are required when is_closed is False")
            if self.open_time >= self.close_time:
                raise ValueError("close_time must be after open_time")
        else:
            self.open_time = None
            self.close_time = None
        return self


class BusinessHourCreate(BusinessHourBase):
    pass


class BusinessHourUpdate(BaseModel):
    is_closed: Optional[bool] = None
    open_time: Optional[time] = None
    close_time: Optional[time] = None


class BusinessHourBulkUpdate(BaseModel):
    """တစ်ပတ်စာ (၇ ရက်) အချိန်များကို တစ်ပြိုင်နက် Update ပြုလုပ်ရန် Schema"""
    schedules: List[BusinessHourCreate]


class BusinessHourResponse(BusinessHourBase):
    id: uuid.UUID
    shop_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)