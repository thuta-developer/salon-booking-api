from typing import Any, Generic, List, Optional, Sequence, Type, TypeVar
import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: uuid.UUID) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def search(
        self, search_term: str, search_fields: List[str], skip: int = 0, limit: int = 20
    ) -> Sequence[ModelType]:
        if not search_term or not search_fields:
            return await self.get_multi(skip=skip, limit=limit)

        search_filter = f"%{search_term}%"
        conditions = []

        for field in search_fields:
            if hasattr(self.model, field):
                column = getattr(self.model, field)
                conditions.append(column.ilike(search_filter))

        if not conditions:
            return []

        stmt = (
            select(self.model)
            .where(or_(*conditions))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in_data: dict[str, Any]) -> ModelType:
        try:
            db_obj = self.model(**obj_in_data)
            self.db.add(db_obj)
            await self.db.commit()
            return db_obj
        except Exception as e:
            await self.db.rollback()
            raise e

    async def create_multi(
        self, obj_in_list: List[dict[str, Any]]
    ) -> Sequence[ModelType]:
        try:
            db_objs = [self.model(**data) for data in obj_in_list]
            self.db.add_all(db_objs)
            await self.db.commit()
            return db_objs
        except Exception as e:
            await self.db.rollback()
            raise e

    async def update(self, db_obj: ModelType, update_data: dict[str, Any]) -> ModelType:
        try:
            for field, value in update_data.items():
                if hasattr(db_obj, field) and value is not None:
                    setattr(db_obj, field, value)
            self.db.add(db_obj)
            await self.db.commit()
            return db_obj
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete(self, id: uuid.UUID) -> bool:
        db_obj = await self.get_by_id(id)
        if db_obj:
            try:
                await self.db.delete(db_obj)
                await self.db.commit()
                return True
            except Exception as e:
                await self.db.rollback()
                raise e
        return False

    async def soft_delete(self, id: uuid.UUID) -> bool:
        db_obj = await self.get_by_id(id)
        if db_obj and hasattr(db_obj, "is_active"):
            try:
                db_obj.is_active = False
                self.db.add(db_obj)
                await self.db.commit()
                return True
            except Exception as e:
                await self.db.rollback()
                raise e
        return False
