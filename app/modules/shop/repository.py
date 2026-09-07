"""Shop module repository — database access."""
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.common.repository import BaseRepository
from app.modules.shop.models import Shop
from app.modules.users.models import User


class ShopRepository(BaseRepository[Shop]):
    def __init__(self, db: AsyncSession):
        super().__init__(Shop, db)

    async def get_by_slug(self, slug: str) -> Optional[Shop]:
        stmt = select(Shop).where(Shop.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_owner(self, shop_id: uuid.UUID) -> Optional[Shop]:
        stmt = (
            select(Shop)
            .options(
                joinedload(Shop.owner).selectinload(User.roles) 
            )
            .where(Shop.id == shop_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_owner_shop_by_id(
        self, shop_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Optional[Shop]:
        stmt = select(Shop).where(Shop.id == shop_id, Shop.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_public_paginated_shops(
        self,
        search: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        is_active: bool = True,
        is_verified: bool = True,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Shop], int]:
        filters = []

        if search:
            search_filter = f"%{search}%"
            filters.append(
                or_(
                    Shop.name.ilike(search_filter),
                    Shop.description.ilike(search_filter),
                )
            )

        if is_active is not None:
            filters.append(Shop.is_active == is_active)

        if is_verified is not None:
            filters.append(Shop.is_verified == is_verified)

        if city:
            filters.append(Shop.city.ilike(f"%{city}%"))

        if country:
            filters.append(Shop.country.ilike(f"%{country}%"))

        count_stmt = select(func.count(Shop.id)).where(*filters)
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        query = (
            select(Shop)
            .where(*filters)
            .order_by(Shop.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_owner_paginated_shops(
        self,
        owner_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Shop], int]:
        count_stmt = select(func.count(Shop.id)).where(Shop.owner_id == owner_id)
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        query = (
            select(Shop)
            .where(Shop.owner_id == owner_id)
            .order_by(Shop.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def soft_delete(self, shop_id: uuid.UUID) -> bool:
        stmt = update(Shop).where(Shop.id == shop_id).values(is_active=False)
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    async def hard_delete(self, shop_id: uuid.UUID) -> bool:
        stmt = delete(Shop).where(Shop.id == shop_id)
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0