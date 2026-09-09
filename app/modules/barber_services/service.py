import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.service import BaseService
from app.modules.barber_services.models import BarberService
from app.modules.barber_services.repository import BarberServiceRepository
from app.modules.barber_services.schemas import (
    BarberServiceBulkAssign,
    BarberServiceDetailResponse,
    BarberServiceResponse,
)
from app.modules.shop_barbers.repository import ShopBarberRepository
from app.modules.services.repository import ServiceRepository
from app.modules.shop.repository import ShopRepository


class BarberServiceService(BaseService[BarberService, BarberServiceRepository]):
    def __init__(self, db: AsyncSession):
        self.repository = BarberServiceRepository(db)
        super().__init__(repository=self.repository)
        self.shop_repo = ShopRepository(db)
        self.barber_repo = ShopBarberRepository(db)
        self.service_repo = ServiceRepository(db)

    async def _verify_shop_ownership(
        self, shop_id: uuid.UUID, owner_id: uuid.UUID
    ) -> None:
        """Shop Owner ဟုတ်မဟုတ် စစ်ဆေးခြင်း"""
        shop = await self.shop_repo.get_by_id(shop_id)
        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
            )
        if shop.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to manage this shop's resources",
            )

    # ==========================================
    # PUBLIC METHODS
    # ==========================================

    async def get_barbers_for_service(
        self, shop_id: uuid.UUID, service_id: uuid.UUID, is_active: Optional[bool] = None
    ) -> List[BarberServiceDetailResponse]:
        """Public: Service တစ်ခုရရှိနိုင်သော Active Barber များကို ပြသခြင်း"""
        service_item = await self.service_repo.get_by_id(service_id)
        if not service_item or service_item.shop_id != shop_id or not service_item.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
            )

        barber_services = await self.repository.get_barbers_by_service(
            service_id=service_id, is_active=is_active
        )
        return [BarberServiceDetailResponse.model_validate(bs) for bs in barber_services]

    async def get_services_for_barber(
        self, shop_id: uuid.UUID, shop_barber_id: uuid.UUID, is_active: Optional[bool] = None
    ) -> List[BarberServiceDetailResponse]:
        """Public: Barber တစ်ယောက် ပြုလုပ်ပေးနိုင်သော Active Service များကို ပြသခြင်း"""
        barber = await self.barber_repo.get_by_id(shop_barber_id)
        if not barber or barber.shop_id != shop_id or not barber.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Barber not found"
            )

        barber_services = await self.repository.get_services_by_barber(
            shop_barber_id=shop_barber_id, is_active=is_active
        )
        return [BarberServiceDetailResponse.model_validate(bs) for bs in barber_services]

    # ==========================================
    # OWNER METHODS
    # ==========================================

    async def get_owner_barber_services(
        self, owner_id: uuid.UUID, shop_barber_id: uuid.UUID, is_active: Optional[bool] = None
    ) -> List[BarberServiceDetailResponse]:
        """Owner: Barber တစ်ယောက်၏ Service အားလုံး (Active/Inactive) ကြည့်ရှုခြင်း"""
        barber = await self.barber_repo.get_by_id(shop_barber_id)
        if not barber:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Barber not found"
            )

        await self._verify_shop_ownership(barber.shop_id, owner_id)

        barber_services = await self.repository.get_services_by_barber(
            shop_barber_id=shop_barber_id, is_active=is_active
        )
        return [BarberServiceDetailResponse.model_validate(bs) for bs in barber_services]

    async def assign_services_to_barber(
        self,
        owner_id: uuid.UUID,
        shop_barber_id: uuid.UUID,
        payload: BarberServiceBulkAssign,
    ) -> List[BarberServiceResponse]:
        """Owner: Barber ထံသို့ Service များကို Assign/Link လုပ်ခြင်း (Bulk Support)"""
        barber = await self.barber_repo.get_by_id(shop_barber_id)
        if not barber:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Barber not found"
            )

        await self._verify_shop_ownership(barber.shop_id, owner_id)

        assigned_records = []
        for service_id in payload.service_ids:
            # Service သည် ယင်း Shop အောက်တွင် ရှိမရှိ စစ်ဆေးခြင်း
            srv = await self.service_repo.get_by_id(service_id)
            if not srv or srv.shop_id != barber.shop_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Service ID {service_id} does not belong to this shop",
                )

            # Record ရှိပြီးသားလား စစ်ဆေးခြင်း
            existing = await self.repository.get_by_barber_and_service(
                shop_barber_id=shop_barber_id, service_id=service_id
            )
            if existing:
                if not existing.is_active:
                    # Inactive ဖြစ်နေလျှင် ပြန် Re-activate လုပ်ခြင်း
                    updated = await self.update(existing, {"is_active": True})
                    await self.repository.db.refresh(updated)
                    assigned_records.append(updated)
                else:
                    assigned_records.append(existing)
            else:
                # မရှိသေးလျှင် အသစ်ဖန်တီးခြင်း
                created = await self.create({
                    "shop_barber_id": shop_barber_id,
                    "service_id": service_id,
                    "is_active": True,
                })
                await self.repository.db.refresh(created)
                assigned_records.append(created)

        return [BarberServiceResponse.model_validate(r) for r in assigned_records]

    async def remove_service_from_barber(
        self,
        owner_id: uuid.UUID,
        shop_barber_id: uuid.UUID,
        service_id: uuid.UUID,
    ) -> dict:
        """Owner: Barber ထံမှ Service တစ်ခုကို Unassign / Delete လုပ်ခြင်း"""
        barber = await self.barber_repo.get_by_id(shop_barber_id)
        if not barber:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Barber not found"
            )

        await self._verify_shop_ownership(barber.shop_id, owner_id)

        existing = await self.repository.get_by_barber_and_service(
            shop_barber_id=shop_barber_id, service_id=service_id
        )
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service association not found for this barber",
            )

        await self.delete(existing.id)
        return {"message": "Service unassigned from barber successfully"}





