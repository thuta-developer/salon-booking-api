import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.common.dependencies import get_current_active_user # Authentication dependency
from app.modules.business_hours.schemas import (
    BusinessHourBulkUpdate,
    BusinessHourResponse,
)
from app.modules.business_hours.service import BusinessHourService
from app.modules.users.models import User

router = APIRouter(prefix="/shops/{shop_id}/business-hours", tags=["Business Hours"])


@router.get(
    "",
    response_model=List[BusinessHourResponse],
    status_code=status.HTTP_200_OK,
    summary="Get shop business hours",
)
async def get_business_hours(
    shop_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Shop တစ်ခု၏ Business Hours (ဖွင့်ချိန်/ပိတ်ချိန်) များကို ရယူရန် Endpoint (Public)
    """
    service = BusinessHourService(db)
    return await service.get_by_shop_id(shop_id=shop_id)


@router.put(
    "",
    response_model=List[BusinessHourResponse],
    status_code=status.HTTP_200_OK,
    summary="Bulk update shop business hours",
)
async def bulk_update_business_hours(
    shop_id: uuid.UUID,
    payload: BusinessHourBulkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Shop ၏ တစ်ပတ်စာ (၇ ရက်) Business Hours များကို တစ်ပြိုင်နက် Update/Create ပြုလုပ်ရန် Endpoint (Authenticated)
    """
    service = BusinessHourService(db)
    return await service.bulk_update_business_hours(
        shop_id=shop_id, payload=payload
    )