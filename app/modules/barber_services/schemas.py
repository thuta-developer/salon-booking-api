import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.modules.services.schemas import ServiceResponse

class BarberServiceBase(BaseModel):
    is_active: bool = True


class BarberServiceCreate(BarberServiceBase):
    shop_barber_id: uuid.UUID
    service_id: uuid.UUID


# Barber တစ်ယောက်တည်းမှာ Service အများအပြား တစ်ပြိုင်နက် Assign လုပ်လိုပါက သုံးနိုင်သော Schema
class BarberServiceBulkAssign(BaseModel):
    shop_barber_id: uuid.UUID
    service_ids: List[uuid.UUID]


class BarberServiceUpdate(BaseModel):
    is_active: Optional[bool] = None


class BarberServiceResponse(BarberServiceBase):
    id: uuid.UUID
    shop_barber_id: uuid.UUID
    service_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Front-end မှာ ပြသရလွယ်ကူစေရန် Service အသေးစိတ်ပါ ပူးတွဲပါဝင်သော Response
class BarberServiceDetailResponse(BarberServiceResponse):
    service: Optional[ServiceResponse] = None

    model_config = ConfigDict(from_attributes=True)