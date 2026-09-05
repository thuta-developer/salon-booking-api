"""Auth module repositories — RBAC (Role / Permission) data access.

The user repository lives in ``app.modules.users.repository``.
"""
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.modules.auth.models import Permission, Role


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name_ci(self, name: str) -> Optional[Role]:
        """Case-insensitive duplicate check — 'Admin' / 'admin' / 'ADMIN' ခွဲထွက်မဖြစ်ရန်"""
        stmt = select(Role).where(func.lower(Role.name) == name.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_permissions(self, role_id: uuid.UUID) -> Optional[Role]:
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
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

    async def update_role_permissions(
        self, role: Role, permissions: List[Permission]
    ) -> Role:
        role.permissions = permissions
        await self.db.commit()
        return role


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, db: AsyncSession):
        super().__init__(Permission, db)

    async def get_by_name(self, name: str) -> Optional[Permission]:
        stmt = select(self.model).where(self.model.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name_ci(self, name: str) -> Optional[Permission]:
        """Case-insensitive duplicate check — 'User:Read' / 'user:read' ခွဲထွက်မဖြစ်ရန်"""
        stmt = select(self.model).where(func.lower(self.model.name) == name.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, permission_ids: List[uuid.UUID]) -> List[Permission]:
        if not permission_ids:
            return []
        stmt = select(Permission).where(Permission.id.in_(permission_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_paginated_permissions(
        self,
        search: Optional[str] = None,
        module: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[Permission], int]:
        query = select(Permission)

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    Permission.name.ilike(search_filter),
                    Permission.description.ilike(search_filter),
                )
            )

        if module:
            query = query.where(Permission.module == module)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Pagination Offset
        offset = (page - 1) * size
        query = (
            query.order_by(Permission.module.asc(), Permission.name.asc())
            .offset(offset)
            .limit(size)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all()), total