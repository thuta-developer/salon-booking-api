import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.service import BaseService
from app.common.pagination import PaginatedResponse
from app.modules.shop_barbers.models import ShopBarber
from app.modules.shop_barbers.repository import ShopBarberRepository
from app.modules.shop_barbers.schemas import (
    ShopBarberCreate,
    ShopBarberResponse,
    ShopBarberUpdate,
)
from app.modules.shop.repository import ShopRepository
from app.modules.users.repository import UserRepository


class ShopBarberService(BaseService[ShopBarber, ShopBarberRepository]):
    def __init__(self, db: AsyncSession):
        self.repository = ShopBarberRepository(db)
        super().__init__(repository=self.repository)
        self.shop_repo = ShopRepository(db)
        self.user_repo = UserRepository(db)

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
                detail="Not authorized to manage this shop's barbers",
            )

    async def add_barber_to_shop(
        self, owner_id: uuid.UUID, shop_id: uuid.UUID, barber_in: ShopBarberCreate
    ) -> ShopBarberResponse:
        await self._verify_shop_ownership(shop_id, owner_id)

        # Barber User ရှိမရှိ စစ်ဆေးခြင်း
        barber_user = await self.user_repo.get_by_id(barber_in.barber_id)
        if not barber_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target barber user not found",
            )

        # Shop ထဲတွင် Barber ရှိနှင့်ပြီးသားလား စစ်ဆေးခြင်း
        existing = await self.repository.get_by_shop_and_barber(
            shop_id, barber_in.barber_id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This barber is already assigned to this shop",
            )

        create_data = {
            "shop_id": shop_id,
            "barber_id": barber_in.barber_id,
            "display_name": barber_in.display_name,
            "bio": barber_in.bio,
            "is_active": barber_in.is_active,
            "joined_at": barber_in.joined_at or datetime.now(timezone.utc),
        }

        try:
            created_barber = await self.create(create_data)
            result = await self.repository.get_by_id_with_relations(created_barber.id)
            return ShopBarberResponse.model_validate(result)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint conflict",
            )

    async def get_shop_barbers(
        self,
        owner_id: uuid.UUID,
        shop_id: uuid.UUID,
        search: Optional[str],
        page: int = 1,
        size: int = 20,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[ShopBarberResponse]:
        await self._verify_shop_ownership(shop_id, owner_id)

        barbers, total = await self.repository.get_paginated_by_shop(
            shop_id=shop_id, search=search , page=page, size=size, is_active=is_active
        )

        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [ShopBarberResponse.model_validate(b) for b in barbers]

        return PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

    async def get_barber_detail(
        self, owner_id: uuid.UUID, shop_barber_id: uuid.UUID
    ) -> ShopBarberResponse:
        barber = await self.repository.get_by_id_with_relations(shop_barber_id)
        if not barber:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Barber record not found"
            )

        await self._verify_shop_ownership(barber.shop_id, owner_id)
        return ShopBarberResponse.model_validate(barber)

    async def update_barber(
        self,
        owner_id: uuid.UUID,
        shop_barber_id: uuid.UUID,
        update_in: ShopBarberUpdate,
    ) -> ShopBarberResponse:
        barber = await self.repository.get_by_id(shop_barber_id)
        if not barber:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Barber record not found"
            )

        await self._verify_shop_ownership(barber.shop_id, owner_id)

        update_data = update_in.model_dump(exclude_unset=True)
        updated_barber = await self.update(barber, update_data)

        # Relationship ပါဝင်အောင် အပြည့်အစုံ ပြန်ဆွဲခြင်း
        result = await self.repository.get_by_id_with_relations(updated_barber.id)
        return ShopBarberResponse.model_validate(result)

    async def delete_barber(
        self, owner_id: uuid.UUID, shop_barber_id: uuid.UUID, is_hard_delete: bool = False
    ) -> dict:
        barber = await self.repository.get_by_id(shop_barber_id)
        if not barber:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Barber record not found"
            )

        await self._verify_shop_ownership(barber.shop_id, owner_id)

        if is_hard_delete:
            # BaseService ရဲ့ hard delete ကို ခေါ်သုံးခြင်း
            await self.delete(shop_barber_id)
            message = "Barber record permanently deleted"
        else:
            # BaseService ရဲ့ soft delete (is_active = False) ကို ခေါ်သုံးခြင်း
            await self.soft_delete(shop_barber_id)
            message = "Barber deactivated (Soft Deleted)"

        return {"message": message}