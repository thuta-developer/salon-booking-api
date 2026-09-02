import uuid
import math
import re
from typing import Optional
from fastapi import HTTPException, status

from app.models.shop import Shop
from app.models.user import User
from app.repositories.shop_repository import ShopRepository
from app.services.base_service import BaseService
from app.schemas.shop import ShopCreate, ShopUpdate, ShopResponse, ShopDetailResponse
from app.schemas.common import PaginatedResponse

class ShopService(BaseService[Shop, ShopRepository]):
    def __init__(self, shop_repository: ShopRepository):
        super().__init__(shop_repository)
        self.shop_repository = shop_repository
        self.db = shop_repository.db

    async def _generate_unique_slug(self, text: str, exclude_id: Optional[uuid.UUID] = None) -> str:
        """Slug အမည်တူနေပါက အလိုအလျောက် counter ပေါင်းထည့်ပေးမည်"""
        base_slug = re.sub(r"[^\w\-]", "-", text.lower()).strip("-")
        base_slug = re.sub(r"\-+", "-", base_slug)
        
        slug = base_slug
        counter = 1
        
        while await self.shop_repository.exists_by_slug(slug, exclude_id):
            slug = f"{base_slug}-{counter}"
            counter += 1
            
        return slug

    async def create_shop(self, shop_in: ShopCreate, current_user: User) -> ShopResponse:
        shop_data = shop_in.model_dump()

        slug = shop_data.get("slug")
        if not slug:
            slug = shop_data["name"]

        shop_data["slug"] = await self._generate_unique_slug(slug)
        shop_data["owner_id"] = current_user.id

        if not current_user.is_superuser:
            shop_data["is_verified"] = False

        created_shop = await self.shop_repository.create(shop_data)
        return ShopResponse.model_validate(created_shop)

    async def get_shop_detail(self, shop_id: uuid.UUID) -> ShopDetailResponse:
        shop = await self.shop_repository.get_by_id_with_owner(shop_id)
        if not shop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
        return ShopDetailResponse.model_validate(shop)

    async def get_shop_by_slug_detail(self, slug: str) -> ShopDetailResponse:
        shop = await self.shop_repository.get_by_slug(slug)
        if not shop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
        return ShopDetailResponse.model_validate(shop)

    async def get_shops_list(
        self,
        search: Optional[str] = None,
        city: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        owner_id: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[ShopResponse]:
        shops, total = await self.shop_repository.get_paginated_shops(
            search=search,
            city=city,
            is_active=is_active,
            is_verified=is_verified,
            owner_id=owner_id,
            page=page,
            size=size
        )

        total_pages = math.ceil(total / size) if size > 0 else 0
        items = [ShopResponse.model_validate(shop) for shop in shops]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )

    async def update_shop(
        self, shop_id: uuid.UUID, shop_in: ShopUpdate, current_user: User
    ) -> ShopResponse:
        shop = await self.shop_repository.get_by_id(shop_id)
        if not shop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
        
        # Guard: ဆိုင်ပိုင်ရှင် သို့မဟုတ် Superuser သာလျှင် ပြင်ခွင့်ရှိသည်
        if shop.owner_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this shop")

        update_data = shop_in.model_dump(exclude_unset=True)

        # Guard: User ရိုးရိုးသည် Verified status ကို ပြင်ခွင့်မရှိပါ
        if "is_verified" in update_data and not current_user.is_superuser:
            del update_data["is_verified"]

        # Slug သို့မဟုတ် Name ပြောင်းလဲပါက Unique ဖြစ်စေရန် ပြန်စစ်မည်
        if "slug" in update_data or "name" in update_data:
            new_text = update_data.get("slug") or update_data.get("name")
            update_data["slug"] = await self._generate_unique_slug(new_text, exclude_id=shop_id)

        updated_shop = await self.shop_repository.update(shop, update_data)
        return ShopResponse.model_validate(updated_shop)

    async def soft_delete_shop(self, shop_id: uuid.UUID, acting_user: User) -> dict:
        shop = await self.shop_repository.get_by_id(shop_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )

        # Owner သို့မဟုတ် Superuser သာ Soft Delete လုပ်ခွင့်ရှိသည်
        if shop.owner_id != acting_user.id and not acting_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this shop",
            )

        await self.shop_repository.soft_delete(shop_id)
        return {"message": "Shop deactivated successfully"}

    async def hard_delete_shop(self, shop_id: uuid.UUID, acting_user: User) -> dict:
        shop = await self.shop_repository.get_by_id(shop_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )

        # Superuser သာ Hard Delete လုပ်ခွင့်ရှိသည်
        if not acting_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can permanently delete shops",
            )

        await self.shop_repository.delete(shop_id)
        return {"message": "Shop permanently deleted successfully"}