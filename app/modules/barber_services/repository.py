import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.modules.barber_services.models import BarberService


class BarberServiceRepository(BaseRepository[BarberService]):
    def __init__(self, db: AsyncSession):
        super().__init__(model=BarberService, db=db)

    async def get_by_barber_and_service(
        self, shop_barber_id: uuid.UUID, service_id: uuid.UUID
    ) -> Optional[BarberService]:
        """Barber တစ်ယောက်နှင့် Service တစ်ခု အတိအကျ တိုက်ဆိုင် record ရှိမရှိ ဆွဲထုတ်ခြင်း"""
        stmt = select(BarberService).where(
            BarberService.shop_barber_id == shop_barber_id,
            BarberService.service_id == service_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_barber_and_services(
        self, shop_barber_id: uuid.UUID, service_ids: List[uuid.UUID]
    ) -> List[BarberService]:
        """Barber ID နှင့် service_ids list ပါ ရှိပြီးသား records များကို Bulk query ရိုက်ခြင်း"""
        if not service_ids:
            return []
        stmt = select(BarberService).where(
            BarberService.shop_barber_id == shop_barber_id,
            BarberService.service_id.in_(service_ids),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_services_by_barber(
        self, shop_barber_id: uuid.UUID, is_active: Optional[bool] = None,
    ) -> List[BarberService]:
        """Barber တစ်ယောက် ရရှိနိုင်သော Service များကို Service + Category data ပါ ပူးတွဲ ဆွဲထုတ်ခြင်း"""
        stmt = (
            select(BarberService)
            .options(
                selectinload(BarberService.service).selectinload(
                    BarberService.service.property.mapper.class_.category
                )
            )
            .where(BarberService.shop_barber_id == shop_barber_id)
        )

        if is_active:
            stmt = stmt.where(BarberService.is_active == is_active)  # noqa: E712

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_barbers_by_service(
        self, service_id: uuid.UUID, is_active: Optional[bool] = None,
    ) -> List[BarberService]:
        """Service တစ်ခုကို ဆောင်ရွက်ပေးနိုင်သော Barber များကို Barber data ပါ ပူးတွဲ ဆွဲထုတ်ခြင်း"""
        stmt = (
            select(BarberService)
            .options(selectinload(BarberService.barber))
            .where(BarberService.service_id == service_id)
        )

        if is_active:
            stmt = stmt.where(BarberService.is_active == is_active)  # noqa: E712

        result = await self.db.execute(stmt)
        return list(result.scalars().all())