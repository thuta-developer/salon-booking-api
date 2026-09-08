import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.repository import BaseRepository
from app.modules.categories.models import ServiceCategory


class ServiceCategoryRepository(BaseRepository[ServiceCategory]):
    def __init__(self, db: AsyncSession):
        super().__init__(model=ServiceCategory, db=db)

    async def get_by_shop_and_name(
            self, shop_id: uuid.UUID, name: str
    ) -> Optional[ServiceCategory]:
        """Shop တစ်ခုအတွင်း Category Name ထပ်မနေစေရန် စစ်ဆေးသည့် Query"""
        stmt = select(ServiceCategory).where(
            ServiceCategory.shop_id == shop_id,
            func.lower(ServiceCategory.name) == name.strip().lower(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_shop(
            self,
            shop_id: uuid.UUID,
            is_active: Optional[bool] = None,
    ) -> List[ServiceCategory]:
        """Shop တစ်ခု၏ Category များအား display_order အလိုက် ဆွဲထုတ်ခြင်း"""
        stmt = select(ServiceCategory).where(ServiceCategory.shop_id == shop_id)

        if is_active is not None:
            stmt = stmt.where(ServiceCategory.is_active == is_active)

        stmt = stmt.order_by(ServiceCategory.display_order.asc(), ServiceCategory.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())