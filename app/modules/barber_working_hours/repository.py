import uuid
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.repository import BaseRepository
from app.modules.barber_working_hours.models import BarberWorkingHour
from app.modules.barber_working_hours.schemas import BarberWorkingHourCreate


class BarberWorkingHourRepository(BaseRepository[BarberWorkingHour]):
    def __init__(self, db: AsyncSession):
        super().__init__(BarberWorkingHour, db)

    async def get_by_barber_id(
        self, shop_barber_id: uuid.UUID
    ) -> Sequence[BarberWorkingHour]:
        """Barber ID အလိုက် Working Hours များကို day_of_week အစီအစဉ်အတိုင်း ရယူသည်။"""
        stmt = (
            select(self.model)
            .where(self.model.shop_barber_id == shop_barber_id)
            .order_by(self.model.day_of_week.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def upsert_bulk(
        self, shop_barber_id: uuid.UUID, hours_data: Sequence[BarberWorkingHourCreate]
    ) -> Sequence[BarberWorkingHour]:
        """
        N+1 Query မဖြစ်စေရန် PostgreSQL ၏ ON CONFLICT DO UPDATE (Upsert) ကို အသုံးပြု၍ 
        တစ်ကြိမ်တည်းဖြင့် Insert/Update ပြုလုပ်သည်။
        """
        if not hours_data:
            return []

        values = [
            {
                "id": uuid.uuid4(),
                "shop_barber_id": shop_barber_id,
                "day_of_week": item.day_of_week,
                "is_active": item.is_active,
                "start_time": item.start_time,
                "end_time": item.end_time,
            }
            for item in hours_data
        ]

        stmt = insert(self.model).values(values)

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["shop_barber_id", "day_of_week"],
            set_={
                "is_active": stmt.excluded.is_active,
                "start_time": stmt.excluded.start_time,
                "end_time": stmt.excluded.end_time,
                "updated_at": stmt.excluded.updated_at,
            },
        ).returning(self.model)

        try:
            result = await self.db.execute(upsert_stmt)
            await self.db.commit()
            return sorted(result.scalars().all(), key=lambda x: x.day_of_week)
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete_by_barber_id(self, shop_barber_id: uuid.UUID) -> bool:
        """Barber တစ်ယောက်၏ Working Hours အားလုံးကို ဖျက်ပစ်သည်။"""
        stmt = delete(self.model).where(self.model.shop_barber_id == shop_barber_id)
        try:
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            raise e