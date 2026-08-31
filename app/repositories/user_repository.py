import uuid
from typing import Optional, Tuple, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import update
from datetime import datetime, timezone

from app.models.user import User
from app.models.rbac import Role
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.email == email)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.phone_number == phone_number)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_email_or_phone(self, email: str, phone_number: str) -> bool:
        stmt = select(func.count(User.id)).where(
            or_(User.email == email, User.phone_number == phone_number)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one() > 0

    async def get_by_id_with_relations(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(Role.permissions))
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_paginated_users(
        self,
        search: Optional[str] = None,
        account_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[User], int]:

        filters = []
        if search:
            search_filter = f"%{search}%"
            filters.append(
                or_(
                    User.full_name.ilike(search_filter),
                    User.email.ilike(search_filter),
                    User.phone_number.ilike(search_filter),
                )
            )

        if account_type:
            filters.append(User.account_type == account_type)

        if is_active is not None:
            filters.append(User.is_active == is_active)

        count_stmt = select(func.count(User.id))
        if filters:
            count_stmt = count_stmt.where(*filters)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        query = select(User).options(selectinload(User.roles).noload(Role.permissions))

        if filters:
            query = query.where(*filters)

        # Pagination Offset
        offset = (page - 1) * size
        query = query.order_by(User.created_at.desc()).offset(offset).limit(size)

        result = await self.db.execute(query)
        users = result.scalars().all()

        return list(users), total

    async def soft_delete(self, id: uuid.UUID) -> bool:
        stmt = (
            update(User)
            .where(User.id == id, User.is_active == True)
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def hard_delete(self, id: uuid.UUID) -> bool:
        from sqlalchemy import delete

        stmt = delete(User).where(User.id == id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0