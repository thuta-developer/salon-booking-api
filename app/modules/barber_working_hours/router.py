import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
# Auth Dependencies (Project Structure အလိုက် Current Active User/Admin dependencies ထည့်ပါ)
from app.common.dependencies import get_current_active_user  
from app.modules.barber_working_hours.schemas import (
    BarberWorkingHourBulkUpdate,
    BarberWorkingHourResponse,
)
from app.modules.barber_working_hours.service import BarberWorkingHourService

router = APIRouter(
    prefix="/barbers/{barber_id}/working-hours",
    tags=["Barber Working Hours"],
)


@router.get(
    "",
    response_model=List[BarberWorkingHourResponse],
    status_code=status.HTTP_200_OK,
    summary="Get working hours for a specific barber",
)
async def get_working_hours(
    barber_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = BarberWorkingHourService(db)
    return await service.get_barber_working_hours(shop_barber_id=barber_id)


@router.put(
    "",
    response_model=List[BarberWorkingHourResponse],
    status_code=status.HTTP_200_OK,
    summary="Update or set working hours for a barber",
)
async def update_working_hours(
    barber_id: uuid.UUID,
    payload: BarberWorkingHourBulkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),  # Authentication စစ်ဆေးရန်
):
    service = BarberWorkingHourService(db)
    return await service.set_barber_working_hours(
        shop_barber_id=barber_id,
        hours_data=payload.schedules,
    )