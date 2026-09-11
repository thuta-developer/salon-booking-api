import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.repository import BaseRepository
from app.modules.shop_barbers.models import ShopBarber


class ShopBarberRepository(BaseRepository[ShopBarber]):
    def __init__(self, db: AsyncSession):
        super().__init__(model=ShopBarber, db=db)

    async def get_by_id_with_relations(
        self, shop_barber_id: uuid.UUID
    ) -> Optional[ShopBarber]:
        """Detail query — ShopBarber has no FK relationships to load."""
        return await self.get_by_id(shop_barber_id)

    async def get_by_shop_and_name(
        self, shop_id: uuid.UUID, display_name: str
    ) -> Optional[ShopBarber]:
        """Shop တစ်ခုအတွင်း Barber နာမည် ထပ်မနေစေရန် စစ်ဆေးသည့် Query"""
        stmt = select(ShopBarber).where(
            ShopBarber.shop_id == shop_id,
            func.lower(ShopBarber.display_name) == display_name.strip().lower(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_paginated_by_shop(
        self,
        shop_id: uuid.UUID,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[ShopBarber], int]:
        """Shop အလိုက် Barber များအား Paginated ပြုလုပ်၍ ဆွဲထုတ်ခြင်း"""
        filters = [ShopBarber.shop_id == shop_id]

        if search:
            search_filter = f"%{search}%"
            filters.append(
                or_(
                    ShopBarber.display_name.ilike(search_filter),
                )
            )

        if is_active is not None:
            filters.append(ShopBarber.is_active == is_active)

        # Count Query
        count_stmt = select(func.count(ShopBarber.id)).where(*filters)
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        # Data Query
        query = (
            select(ShopBarber)
            .where(*filters)
            .order_by(ShopBarber.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total