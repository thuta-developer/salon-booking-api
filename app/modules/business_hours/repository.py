import uuid
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.repository import BaseRepository
from app.modules.business_hours.models import BusinessHour
from app.modules.business_hours.schemas import BusinessHourCreate

class BusinessHourRepository(BaseRepository[BusinessHour]):
    def __init__(self, db: AsyncSession):
        super().__init__(BusinessHour, db)

    async def get_by_shop_id(self, shop_id: uuid.UUID) -> Sequence[BusinessHour]:
        """Shop ID အလိုက် Business Hours များကို day_of_week အစီအစဉ်အတိုင်း ရယူသည်။"""
        stmt = (
            select(self.model)
            .where(self.model.shop_id == shop_id)
            .order_by(self.model.day_of_week.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


    async def upsert_bulk(
        self, shop_id: uuid.UUID, hours_data: Sequence[BusinessHourCreate]
    ) -> Sequence[BusinessHour]:
        if not hours_data:
            return []

        values = [
            {
                "id": uuid.uuid4(),
                "shop_id": shop_id,
                "day_of_week": item.day_of_week,
                "is_closed": item.is_closed,
                "open_time": item.open_time,
                "close_time": item.close_time,
            }
            for item in hours_data
        ]

        stmt = insert(self.model).values(values)

        # constraint="ix_business_hours_shop_day" အစား index_elements ဖြင့် ပြောင်းပါ
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["shop_id", "day_of_week"],
            set_={
                "is_closed": stmt.excluded.is_closed,
                "open_time": stmt.excluded.open_time,
                "close_time": stmt.excluded.close_time,
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

    async def delete_by_shop_id(self, shop_id: uuid.UUID) -> bool:
        """Shop တစ်ခု၏ Business Hours အားလုံးကို ဖျက်ပစ်သည်။"""
        stmt = delete(self.model).where(self.model.shop_id == shop_id)
        try:
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            raise e