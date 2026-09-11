import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.service import BaseService
from app.modules.categories.models import ServiceCategory
from app.modules.categories.repository import ServiceCategoryRepository
from app.modules.categories.schemas import (
    ServiceCategoryCreate,
    ServiceCategoryResponse,
    ServiceCategoryUpdate,
)
from app.modules.shop.repository import ShopRepository

class ServiceCategoryService(BaseService[ServiceCategory, ServiceCategoryRepository]):
    def __init__(self, db: AsyncSession):
        self.repository = ServiceCategoryRepository(db)
        super().__init__(repository=self.repository)
        self.shop_repo = ShopRepository(db)

    async def _verify_shop_ownership(
        self, shop_id: uuid.UUID, owner_id: uuid.UUID
    ) -> None:
        """Shop Owner ဟုတ်မဟုတ် စစ်ဆေးပေးသည့် Helper"""
        shop = await self.shop_repo.get_by_id(shop_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )
        if shop.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to manage this shop's categories",
            )

    # ==========================================
    # PUBLIC METHODS
    # ==========================================

    async def get_public_categories(self, shop_id: uuid.UUID, is_active: Optional[bool]) -> List[ServiceCategoryResponse]:
        categories = await self.repository.get_by_shop(shop_id=shop_id, is_active=is_active)
        return [ServiceCategoryResponse.model_validate(c) for c in categories]

    async def get_public_category_detail(self, shop_id: uuid.UUID, category_id: uuid.UUID) -> ServiceCategoryResponse:
        category = await self.repository.get_by_id(category_id)
        if not category or category.shop_id != shop_id or not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )
        return ServiceCategoryResponse.model_validate(category)

    # ==========================================
    # OWNER METHODS
    # ==========================================

    async def create_category(
            self, owner_id: uuid.UUID, shop_id: uuid.UUID, cat_in: ServiceCategoryCreate
    ) -> ServiceCategoryResponse:
        await self._verify_shop_ownership(shop_id, owner_id)

        existing = await self.repository.get_by_shop_and_name(
            shop_id=shop_id, name=cat_in.name
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists",
            )

        create_data = cat_in.model_dump()
        create_data["shop_id"] = shop_id

        try:
            created_cat = await self.create(create_data)
            return ServiceCategoryResponse.model_validate(created_cat)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint error",
            )

    async def get_owner_categories(
        self, owner_id: uuid.UUID, shop_id: uuid.UUID, is_active: Optional[bool]
    ) -> List[ServiceCategoryResponse]:
        await self._verify_shop_ownership(shop_id, owner_id)
        categories = await self.repository.get_by_shop(shop_id=shop_id, is_active=is_active)
        return [ServiceCategoryResponse.model_validate(c) for c in categories]

    async def get_owner_category_detail(
        self, owner_id: uuid.UUID, category_id: uuid.UUID
    ) -> ServiceCategoryResponse:
        category = await self.repository.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )

        await self._verify_shop_ownership(category.shop_id, owner_id)
        return ServiceCategoryResponse.model_validate(category)

    async def update_category(
        self,
        owner_id: uuid.UUID,
        category_id: uuid.UUID,
        update_in: ServiceCategoryUpdate,
    ) -> ServiceCategoryResponse:
        category = await self.repository.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )

        await self._verify_shop_ownership(category.shop_id, owner_id)

        update_data = update_in.model_dump(exclude_unset=True)

        # Check name conflict if updating name
        if "name" in update_data and update_data["name"] != category.name:
            existing = await self.repository.get_by_shop_and_name(
                shop_id=category.shop_id, name=update_data["name"]
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category name already exists in this shop",
                )

        updated_cat = await self.update(category, update_data)
        return ServiceCategoryResponse.model_validate(updated_cat)

    async def delete_category(
        self, owner_id: uuid.UUID, category_id: uuid.UUID, hard_delete: bool = False
    ) -> dict:
        category = await self.repository.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )

        await self._verify_shop_ownership(category.shop_id, owner_id)

        if hard_delete:
            await self.delete(category_id)
            message = "Category permanently deleted"
        else:
            await self.soft_delete(category_id)
            message = "Category deactivated (Soft deleted)"

        return {"message": message}