import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.modules.services.models import Service

class ServiceRepository(BaseRepository[Service]):
    def __init__(self , db: AsyncSession):
        super().__init__(model=Service ,db=db)

    async def get_by_shop_and_name(
        self, shop_id: uuid.UUID, name: str,
    ) -> Optional[Service]:
        """Shop တစ်ခုအတွင်း Service Name ထပ်မနေစေရန် စစ်ဆေးသည့် Query"""
        stmt = select(Service).where(
            Service.shop_id == shop_id,
            func.lower(Service.name) == name.strip().lower(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_shop(
        self, shop_id: uuid.UUID, category_id: Optional[uuid.UUID] = None, is_active: Optional[bool] = None,
    ) -> List[Service]:
        """Shop တစ်ခု၏ Service များကို category_id filter ပါဝင်စွာ ဆွဲထုတ်ခြင်း"""
        stmt = (
            select(Service)
            .options(selectinload(Service.category))
            .where(Service.shop_id == shop_id)
        )

        if category_id is not None:
            stmt = stmt.where(Service.category_id == category_id)

        if is_active is not None:
            stmt = stmt.where(Service.is_active == is_active)

        stmt = stmt.order_by(Service.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_with_category(
        self, service_id:uuid.UUID
    ) -> Optional[List[Service]]:
        """Service ကို Category Relationship ပါ ပူးတွဲ ဆွဲထုတ်ခြင်း"""
        stmt = (
            select(Service)
            .options(selectinload(Service.category))
            .where(Service.category_id == service_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
