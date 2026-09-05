"""Generic service base (used by module services)."""
from typing import Any, Generic, List, Optional, Sequence, TypeVar

import uuid

from app.common.repository import BaseRepository

ModelType = TypeVar("ModelType")
RepoType = TypeVar("RepoType", bound=BaseRepository)


class BaseService(Generic[ModelType, RepoType]):
    def __init__(self, repository: RepoType):
        self.repository = repository

    async def get_by_id(self, id: uuid.UUID) -> Optional[ModelType]:
        return await self.repository.get_by_id(id)

    async def get_multi(
        self, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def count(self) -> int:
        return await self.repository.count()

    async def create(self, obj_in_data: dict[str, Any]) -> ModelType:
        return await self.repository.create(obj_in_data)

    async def create_multi(
        self, obj_in_list: List[dict[str, Any]]
    ) -> Sequence[ModelType]:
        return await self.repository.create_multi(obj_in_list)

    async def update(
        self, db_obj: ModelType, update_data: dict[str, Any]
    ) -> ModelType:
        return await self.repository.update(db_obj, update_data)

    async def delete(self, id: uuid.UUID) -> bool:
        return await self.repository.delete(id)

    async def soft_delete(self, id: uuid.UUID) -> bool:
        return await self.repository.soft_delete(id)

    async def search(
        self,
        search_term: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[ModelType]:
        return await self.repository.search(
            search_term=search_term,
            search_fields=search_fields,
            skip=skip,
            limit=limit,
        )