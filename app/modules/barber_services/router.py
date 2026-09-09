import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.common.dependencies import get_current_active_user
from app.modules.barber_services.schemas import (
    BarberServiceBulkAssign,
    BarberServiceDetailResponse,
    BarberServiceResponse,
)
from app.modules.barber_services.service import BarberServiceService
from app.modules.users.models import User

# Router Declarations
public_router = APIRouter(prefix="/shops", tags=["Public - Barber Services"])
owner_router = APIRouter(prefix="/owner", tags=["Shop Owner - Barber Services"])


def get_barber_service_service(
    db: AsyncSession = Depends(get_db),
) -> BarberServiceService:
    return BarberServiceService(db)


# ==========================================
# PUBLIC / CUSTOMER ENDPOINTS
# ==========================================

@public_router.get(
    "/{shop_id}/services/{service_id}/barbers",
    response_model=List[BarberServiceDetailResponse],
)
async def get_barbers_by_service(
    shop_id: uuid.UUID,
    service_id: uuid.UUID,
    is_active: Optional[bool] = Query(None, description="Is active filter"),
    service: BarberServiceService = Depends(get_barber_service_service),
):
    """Public: သတ်မှတ် Service ကို ပြုလုပ်ပေးနိုင်သော Barber များကို ကြည့်ရှုခြင်း"""
    return await service.get_barbers_for_service(
        shop_id=shop_id, service_id=service_id, is_active=is_active
    )


@public_router.get(
    "/{shop_id}/barbers/{shop_barber_id}/services",
    response_model=List[BarberServiceDetailResponse],
)
async def get_services_by_barber(
    shop_id: uuid.UUID,
    shop_barber_id: uuid.UUID,
    service: BarberServiceService = Depends(get_barber_service_service),
):
    """Public: သတ်မှတ် Barber ပြုလုပ်ပေးနိုင်သော Service များကို ကြည့်ရှုခြင်း"""
    return await service.get_services_for_barber(
        shop_id=shop_id, shop_barber_id=shop_barber_id
    )


# ==========================================
# SHOP OWNER ENDPOINTS
# ==========================================

@owner_router.get(
    "/shop-barbers/{shop_barber_id}/services",
    response_model=List[BarberServiceDetailResponse],
)
async def get_owner_barber_services(
    shop_barber_id: uuid.UUID,
    is_active: Optional[bool] = Query(None, description="Is active filter"),
    current_user: User = Depends(get_current_active_user),
    service: BarberServiceService = Depends(get_barber_service_service),
):
    """Shop Owner: Barber တစ်ယောက်၏ Assign လုပ်ထားသော Service အားလုံးကို ကြည့်ရှုခြင်း"""
    return await service.get_owner_barber_services(
        owner_id=current_user.id, shop_barber_id=shop_barber_id, is_active=is_active
    )


@owner_router.post(
    "/shop-barbers/{shop_barber_id}/services",
    response_model=List[BarberServiceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def assign_services_to_barber(
    shop_barber_id: uuid.UUID,
    payload: BarberServiceBulkAssign,
    current_user: User = Depends(get_current_active_user),
    service: BarberServiceService = Depends(get_barber_service_service),
):
    """Shop Owner: Barber ထံသို့ Service များ Assign လုပ်ခြင်း"""
    return await service.assign_services_to_barber(
        owner_id=current_user.id,
        shop_barber_id=shop_barber_id,
        payload=payload,
    )


@owner_router.delete(
    "/shop-barbers/{shop_barber_id}/services/{service_id}",
    status_code=status.HTTP_200_OK,
)
async def remove_service_from_barber(
    shop_barber_id: uuid.UUID,
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: BarberServiceService = Depends(get_barber_service_service),
):
    """Shop Owner: Barber ထံမှ Service ကို Unassign ပြုလုပ်ခြင်း"""
    return await service.remove_service_from_barber(
        owner_id=current_user.id,
        shop_barber_id=shop_barber_id,
        service_id=service_id,
    )