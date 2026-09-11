import uuid
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.barber_working_hours.repository import BarberWorkingHourRepository
from app.modules.barber_working_hours.schemas import (
    BarberWorkingHourCreate,
    BarberWorkingHourResponse,
)
from app.modules.shop_barbers.repository import ShopBarberRepository  # Project Structure အတိုင်း စစ်ဆေးပေးပါ


class BarberWorkingHourService:
    def __init__(self, db: AsyncSession):
        self.repository = BarberWorkingHourRepository(db)
        self.barber_repo = ShopBarberRepository(db)

    async def get_barber_working_hours(
        self, shop_barber_id: uuid.UUID
    ) -> Sequence[BarberWorkingHourResponse]:
        """Barber ၏ Working Hours များကို ဆွဲထုတ်ခြင်း"""
        # Barber အမှန်တကယ် ရှိမရှိ စစ်ဆေးခြင်း
        barber = await self.barber_repo.get_by_id(shop_barber_id)
        if not barber:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Barber not found",
            )
        return await self.repository.get_by_barber_id(shop_barber_id)

    async def set_barber_working_hours(
        self, shop_barber_id: uuid.UUID, hours_data: Sequence[BarberWorkingHourCreate]
    ) -> Sequence[BarberWorkingHourResponse]:
        """Barber ၏ Working Hours များကို သတ်မှတ်/ပြင်ဆင်ခြင်း"""
        # Barber ရှိမရှိ စစ်ဆေးခြင်း
        barber = await self.barber_repo.get_by_id(shop_barber_id)
        if not barber:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Barber not found",
            )

        # Duplicate day_of_week ပါမပါ စစ်ဆေးခြင်း
        days = [item.day_of_week for item in hours_data]
        if len(days) != len(set(days)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate days of week found in the request payload",
            )

        return await self.repository.upsert_bulk(shop_barber_id, hours_data)