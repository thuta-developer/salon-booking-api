import uuid
from typing import Optional, Tuple, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Role, Permission
from app.repositories.base_repository import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_permissions(self, role_id: uuid.UUID) -> Optional[Role]:
        stmt = select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, role_ids: List[uuid.UUID]) -> List[Role]:
        stmt = select(Role).where(Role.id.in_(role_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_paginated_roles(
            self,
            search: Optional[str] = None,
            page: int = 1,
            size: int = 10,
    ) -> Tuple[List[Role], int]:
        # 1. Search Filter သီးသန့်ထုတ်ခြင်း
        filters = []
        if search:
            search_filter = f"%{search}%"
            filters.append(
                or_(
                    Role.name.ilike(search_filter),
                    Role.description.ilike(search_filter),
                )
            )

        # 2. Total Count အတွက် Lightweight Query သုံးခြင်း (selectinload မပါဘဲ)
        count_stmt = select(func.count(Role.id))
        if filters:
            count_stmt = count_stmt.where(*filters)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        if total == 0:
            return [], 0

        # 3. Pagination + Eager loading Data Query
        offset = (page - 1) * size
        stmt = select(Role).options(selectinload(Role.permissions))
        if filters:
            stmt = stmt.where(*filters)

        stmt = stmt.order_by(Role.created_at.desc()).offset(offset).limit(size)

        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_role_permissions(self, role: Role, permissions: List[Permission]) -> Role:
        role.permissions = permissions
        await self.db.commit()
        return role