"""Shop module service — business logic."""
import math
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.common.pagination import PaginatedResponse
from app.common.service import BaseService
from app.common.utils import slugify
from app.modules.shop.models import Shop
from app.modules.shop.repository import ShopRepository
from app.modules.shop.schemas import (
    ShopAdminStatusUpdate,
    ShopAdminVerificationUpdate,
    ShopCreate,
    ShopDetailResponse,
    ShopOwnerUpdate,
    ShopResponse,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.modules.auth.models import Role
from app.modules.users.models import User

class ShopService(BaseService[Shop, ShopRepository]):
    def __init__(self, shop_repository: ShopRepository):
        super().__init__(shop_repository)
        self.shop_repo = shop_repository
        self.db = shop_repository.db

    async def _generate_unique_slug(self, name: str, provided_slug: Optional[str] = None) -> str:
        base_slug = slugify(provided_slug or name)
        slug = base_slug
        count = 1

        while True:
            existing = await self.shop_repo.get_by_slug(slug)
            if not existing:
                return slug
            slug = f"{base_slug}-{count}"
            count += 1

    async def create_shop(self, owner_id: uuid.UUID, shop_in: ShopCreate) -> ShopResponse:
        shop_data = shop_in.model_dump()
        slug = await self._generate_unique_slug(shop_data["name"], shop_data.get("slug"))
        shop_data["slug"] = slug

        # 1. Shop Instance တည်ဆောက်ခြင်း
        shop = Shop(
            **shop_data,
            owner_id=owner_id,
            is_active=True,
            is_verified=False,
        )
        self.db.add(shop)

        # 2. Owner User ကို Roles အတူတကွ (Eager Load) ဆွဲယူခြင်း
        user_stmt = select(User).options(selectinload(User.roles)).where(User.id == owner_id)
        user_res = await self.db.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # 3. DB မှ "Shop Owner" Role ကို ရှာပြီး User ထံ အလိုအလျောက် ပေါင်းထည့်ပေးခြင်း
        role_stmt = select(Role).where(Role.name == "Shop Owner")
        role_res = await self.db.execute(role_stmt)
        shop_owner_role = role_res.scalar_one_or_none()

        if shop_owner_role:
            existing_role_names = [role.name for role in user.roles]
            if "Shop Owner" not in existing_role_names:
                user.roles.append(shop_owner_role)
                self.db.add(user)

        # 4. DB Commit & Refresh ပြုလုပ်ခြင်း
        try:
            await self.db.commit()
            await self.db.refresh(shop)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop slug or email already in use",
            )

        return ShopResponse.model_validate(shop)


    async def get_public_shops(
        self,
        search: Optional[str],
        city: Optional[str],
        country: Optional[str],
        is_active: Optional[bool],
        is_verified: Optional[bool],
        page: int,
        size: int,
    ) -> PaginatedResponse[ShopResponse]:
        shops, total = await self.shop_repo.get_public_paginated_shops(
            search=search, city=city, country=country, is_active=is_active, is_verified=is_verified, page=page, size=size
        )
        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [ShopResponse.model_validate(s) for s in shops]
        return PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

    async def get_public_shop_detail(self, shop_id: uuid.UUID) -> ShopDetailResponse:
        shop = await self.shop_repo.get_by_id_with_owner(shop_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )
        return ShopDetailResponse.model_validate(shop)


    async def get_owner_shops(
        self, owner_id: uuid.UUID, page: int, size: int
    ) -> PaginatedResponse[ShopResponse]:
        shops, total = await self.shop_repo.get_owner_paginated_shops(
            owner_id=owner_id, page=page, size=size
        )
        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [ShopResponse.model_validate(s) for s in shops]
        return PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

    async def get_owner_shop_detail(
        self, shop_id: uuid.UUID, owner_id: uuid.UUID
    ) -> ShopResponse:
        shop = await self.shop_repo.get_owner_shop_by_id(shop_id, owner_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )
        return ShopResponse.model_validate(shop)

    async def update_owner_shop(
        self, shop_id: uuid.UUID, owner_id: uuid.UUID, shop_in: ShopOwnerUpdate
    ) -> ShopResponse:
        shop = await self.shop_repo.get_owner_shop_by_id(shop_id, owner_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )

        update_data = shop_in.model_dump(exclude_unset=True)

        if "slug" in update_data and update_data["slug"]:
            if update_data["slug"] != shop.slug:
                update_data["slug"] = await self._generate_unique_slug(
                    shop.name, update_data["slug"]
                )

        for field, value in update_data.items():
            setattr(shop, field, value)

        self.db.add(shop)
        try:
            await self.db.commit()
            await self.db.refresh(shop)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop slug or email already in use",
            )
        return ShopResponse.model_validate(shop)

    async def admin_update_status(
        self, shop_id: uuid.UUID, status_in: ShopAdminStatusUpdate
    ) -> ShopResponse:
        shop = await self.shop_repo.get_by_id(shop_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )
        shop.is_active = status_in.is_active
        self.db.add(shop)
        await self.db.commit()
        await self.db.refresh(shop)
        return ShopResponse.model_validate(shop)

    async def admin_update_verification(
        self, shop_id: uuid.UUID, verification_in: ShopAdminVerificationUpdate
    ) -> ShopResponse:
        shop = await self.shop_repo.get_by_id(shop_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )
        shop.is_verified = verification_in.is_verified
        self.db.add(shop)
        await self.db.commit()
        await self.db.refresh(shop)
        return ShopResponse.model_validate(shop)

    async def admin_delete_shop(
        self, shop_id: uuid.UUID, is_hard_delete: bool = False
    ) -> dict:
        shop = await self.shop_repo.get_by_id(shop_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )

        if is_hard_delete:
            await self.shop_repo.hard_delete(shop_id)
            return {"message": "Shop permanently deleted"}
        else:
            await self.shop_repo.soft_delete(shop_id)
            return {"message": "Shop deactivated (soft deleted)"}