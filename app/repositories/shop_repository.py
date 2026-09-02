import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shop import Shop
from app.repositories.base_repository import BaseRepository

class ShopRepository(BaseRepository[Shop]):
    def __init__(self, db: AsyncSession):
        super().__init__(Shop, db)

    async def get_by_slug(self, slug: str) -> Optional[Shop]:
        stmt = select(Shop).options(selectinload(Shop.owner)).where(Shop.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_slug(self, slug: str, exclude_id: Optional[uuid.UUID]= None) -> bool:
        stmt = select(func.count(Shop.id)).where(Shop.slug == slug)
        if exclude_id:
            stmt = stmt.where(Shop.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one() > 0

    async def get_by_id_with_owner(self, shop_id: uuid.UUID) -> Optional[Shop]:
        stmt = select(Shop).options(selectinload(Shop.owner)).where(Shop.id == shop_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_paginated_shops(
        self,
        search: Optional[str] = None,
        city: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        owner_id: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Shop], int]:
        filters = []

        if search:
            search_filter = f"%{search}%"
            filters.append(
                or_(
                    Shop.name.ilike(search_filter),
                    Shop.description.ilike(search_filter)
                )
            )

        if city:
            filters.append(Shop.city.ilike(f"%{city}%"))

        if is_active is not None:
            filters.append(Shop.is_active == is_active)
            
        if is_verified is not None:
            filters.append(Shop.is_verified == is_verified)
            
        if owner_id:
            filters.append(Shop.owner_id == owner_id)

        count_stmt = select(func.count(Shop.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        query = select(Shop).options(selectinload(Shop.owner))
        if filters:
            query = query.where(*filters)

        offset = (page - 1) * size
        query = query.order_by(Shop.created_at.desc()).offset(offset).limit(size)

        result = await self.db.execute(query)
        shops = result.scalars().all()

        return list(shops), total