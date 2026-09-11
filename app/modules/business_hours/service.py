import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.service import BaseService
from app.modules.business_hours.models import BusinessHour
from app.modules.business_hours.repository import BusinessHourRepository
from app.modules.business_hours.schemas import BusinessHourBulkUpdate
from app.modules.shop.repository import ShopRepository


class BusinessHourService(BaseService[BusinessHour, BusinessHourRepository]):
    def __init__(self, db: AsyncSession):
        repository = BusinessHourRepository(db)
        super().__init__(repository)
        self.shop_repository = ShopRepository(db)

    async def _ensure_shop_exists(self, shop_id: uuid.UUID) -> None:
        """Shop ရှိမရှိ စစ်ဆေးသည့် Helper Method"""
        shop = await self.shop_repository.get_by_id(shop_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop with ID '{shop_id}' not found",
            )

    async def get_by_shop_id(self, shop_id: uuid.UUID) -> Sequence[BusinessHour]:
        """Shop ၏ Business Hours များကို ရယူမည်။"""
        await self._ensure_shop_exists(shop_id)
        return await self.repository.get_by_shop_id(shop_id)

    async def bulk_update_business_hours(
        self, shop_id: uuid.UUID, payload: BusinessHourBulkUpdate
    ) -> Sequence[BusinessHour]:
        """Shop ၏ တစ်ပတ်စာ Business Hours များကို Upsert ပြုလုပ်မည်။"""
        await self._ensure_shop_exists(shop_id)

        # Duplicate day_of_week ပါမပါ စစ်ဆေးခြင်း
        days = [item.day_of_week for item in payload.schedules]
        if len(days) != len(set(days)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate day_of_week entries are not allowed in the request",
            )

        return await self.repository.upsert_bulk(
            shop_id=shop_id, hours_data=payload.schedules
        )