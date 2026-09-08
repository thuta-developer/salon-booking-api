import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_active_user, get_db
from app.common.pagination import PaginatedResponse
from app.modules.shop_barbers.schemas import (
    ShopBarberCreate,
    ShopBarberResponse,
    ShopBarberUpdate,
)
from app.modules.shop_barbers.service import ShopBarberService
from app.modules.users.models import User

router = APIRouter(prefix="/owner", tags=["Shop Owner - Barbers"])


def get_barber_service(db: AsyncSession = Depends(get_db)) -> ShopBarberService:
    return ShopBarberService(db)

@router.post(
    "/shops/{shop_id}/barbers",
    response_model=ShopBarberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_barber_to_shop(
    shop_id: uuid.UUID,
    barber_in: ShopBarberCreate,
    current_user: User = Depends(get_current_active_user),
    service: ShopBarberService = Depends(get_barber_service),
):
    """Shop Owner: Shop ထဲသို့ Barber အသစ် ထည့်သွင်းခြင်း"""
    return await service.add_barber_to_shop(
        owner_id=current_user.id, shop_id=shop_id, barber_in=barber_in
    )


@router.get(
    "/shops/{shop_id}/barbers",
    response_model=PaginatedResponse[ShopBarberResponse],
)
async def list_shop_barbers(
    shop_id: uuid.UUID,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search : Optional[str] = Query(None, description="Search by name"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    service: ShopBarberService = Depends(get_barber_service),
):
    """Shop Owner: မိမိ Shop ရှိ Barber များ စာရင်းကို ကြည့်ရှုခြင်း"""
    return await service.get_shop_barbers(
        owner_id=current_user.id,
        shop_id=shop_id,
        search=search,
        page=page,
        size=size,
        is_active=is_active,
    )


@router.get(
    "/shop-barbers/{shop_barber_id}",
    response_model=ShopBarberResponse,
)
async def get_shop_barber_detail(
    shop_barber_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: ShopBarberService = Depends(get_barber_service),
):
    """Shop Owner: Barber အသေးစိတ်ကြည့်ရှုခြင်း"""
    return await service.get_barber_detail(
        owner_id=current_user.id, shop_barber_id=shop_barber_id
    )


@router.patch(
    "/shop-barbers/{shop_barber_id}",
    response_model=ShopBarberResponse,
)
async def update_shop_barber(
    shop_barber_id: uuid.UUID,
    update_in: ShopBarberUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ShopBarberService = Depends(get_barber_service),
):
    """Shop Owner: Barber အချက်အလက် ပြင်ဆင်ခြင်း"""
    return await service.update_barber(
        owner_id=current_user.id,
        shop_barber_id=shop_barber_id,
        update_in=update_in,
    )


@router.delete(
    "/shop-barbers/{shop_barber_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_shop_barber(
    shop_barber_id: uuid.UUID,
    hard_delete: bool = Query(
        False, description="True ပေးပါက Permanent Delete လုပ်မည် ဖြစ်သည်"
    ),
    current_user: User = Depends(get_current_active_user),
    service: ShopBarberService = Depends(get_barber_service),
):
    """Shop Owner: Barber ကို Soft Delete (is_active=False) သို့မဟုတ် Hard Delete ပြုလုပ်ခြင်း"""
    return await service.delete_barber(
        owner_id=current_user.id,
        shop_barber_id=shop_barber_id,
        is_hard_delete=hard_delete,
    )