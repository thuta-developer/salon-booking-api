import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.service import BaseService
from app.modules.categories.repository import ServiceCategoryRepository
from app.modules.services.models import Service
from app.modules.services.repository import ServiceRepository
from app.modules.services.schemas import (
    ServiceCreate,
    ServiceDetailResponse,
    ServiceResponse,
    ServiceUpdate,
)
from app.modules.shop.repository import ShopRepository

class ServiceService(BaseService[Service, ServiceRepository]):
    def __init__(self, db: AsyncSession):
        self.repository = ServiceRepository(db)
        super().__init__(repository=self.repository)
        self.shop_repo = ShopRepository(db)
        self.category_repo = ServiceCategoryRepository(db)

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
                detail="Not authorized to manage this shop's services",
            )

    # ==========================================
    # PUBLIC METHODS
    # ==========================================

    async def get_public_services(
        self , shop_id: uuid.UUID, category_id: Optional[uuid.UUID] = None, is_active: Optional[bool] = None
    ) -> List[ServiceDetailResponse]:
        services = await self.repository.get_by_shop(
            shop_id=shop_id, category_id=category_id, is_active=is_active
        )
        return [ServiceDetailResponse.model_validate(s) for s in services]

    async def get_public_service_detail(
            self, shop_id: uuid.UUID, service_id: uuid.UUID
    ) -> ServiceDetailResponse:
        service_item = await self.repository.get_with_category(service_id)
        if not service_item or service_item.shop_id != shop_id or not service_item.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
            )
        return ServiceDetailResponse.model_validate(service_item)

    # ==========================================
    # OWNER METHODS
    # ==========================================

    async def create_service(
        self, owner_id: uuid.UUID, shop_id: uuid.UUID, service_in: ServiceCreate
    ) -> ServiceResponse:
        await self._verify_shop_ownership(shop_id, owner_id)

        # Category ထီးအောက်မှာ တကယ်ရှိမရှိနှင့် Active ဖြစ်မဖြစ် စစ်ဆေးခြင်း
        category = await self.category_repo.get_by_id(service_in.category_id)
        if not category or category.shop_id != shop_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Category ID for this shop",
            )

        # Service Name Duplicate Check
        existing = await self.repository.get_by_shop_and_name(
            shop_id=shop_id, name=service_in.name
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service with this name already exists in the shop",
            )

        create_data = service_in.model_dump()
        create_data["shop_id"] = shop_id

        try:
            created_service = await self.create(create_data)
            return ServiceResponse.model_validate(created_service)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint error",
            )

    async def update_service(
        self,
        owner_id: uuid.UUID,
        service_id: uuid.UUID,
        update_in: ServiceUpdate,
    ) -> ServiceResponse:
        service_item = await self.repository.get_by_id(service_id)
        if not service_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
            )

        await self._verify_shop_ownership(service_item.shop_id, owner_id)

        update_data = update_in.model_dump(exclude_unset=True)

        # Update category_id ကို စစ်ဆေးခြင်း
        if "category_id" in update_data and update_data["category_id"] is not None:
            category = await self.category_repo.get_by_id(update_data["category_id"])
            if not category or category.shop_id != service_item.shop_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Category ID for this shop",
                )

        # Update name conflict စစ်ဆေးခြင်း
        if "name" in update_data and update_data["name"] != service_item.name:
            existing = await self.repository.get_by_shop_and_name(
                shop_id=service_item.shop_id, name=update_data["name"]
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Service name already exists in this shop",
                )

        updated_service = await self.update(service_item, update_data)
        return ServiceResponse.model_validate(updated_service)

    async def delete_service(
        self, owner_id: uuid.UUID, service_id: uuid.UUID, hard_delete: bool = False
    ) -> dict:
        service_item = await self.repository.get_by_id(service_id)
        if not service_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
            )

        await self._verify_shop_ownership(service_item.shop_id, owner_id)

        if hard_delete:
            await self.delete(service_id)
            message = "Service permanently deleted"
        else:
            await self.soft_delete(service_id)
            message = "Service deactivated (Soft deleted)"

        return {"message": message}

