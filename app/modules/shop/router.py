"""Shop module HTTP endpoints."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_active_user, get_db, has_permission
from app.common.pagination import PaginatedResponse
from app.modules.shop.repository import ShopRepository
from app.modules.shop.schemas import (
    ShopAdminStatusUpdate,
    ShopAdminVerificationUpdate,
    ShopCreate,
    ShopDetailResponse,
    ShopOwnerUpdate,
    ShopResponse,
)
from app.modules.shop.service import ShopService
from app.modules.users.models import User

router = APIRouter(prefix="/shops", tags=["Shops"])


def get_shop_service(db: AsyncSession = Depends(get_db)) -> ShopService:
    return ShopService(ShopRepository(db))


# ==========================================
# PUBLIC ENDPOINTS
# ==========================================
@router.get("", response_model=PaginatedResponse[ShopResponse])
async def list_public_shops(
    search: Optional[str] = Query(None, description="Search by shop name or description"),
    city: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verified status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: ShopService = Depends(get_shop_service),
):
    """Public: Active ဖြစ်သော Shop များ စာရင်းကို ကြည့်ရှုခြင်း"""
    return await service.get_public_shops(
        search=search, city=city, country=country, page=page, size=size, is_active=is_active, is_verified=is_verified
    )


@router.get("/{shop_id}", response_model=ShopDetailResponse)
async def get_public_shop(
    shop_id: uuid.UUID,
    service: ShopService = Depends(get_shop_service),
):
    """Public: Active ဖြစ်သော Shop တစ်ခု၏ အသေးစိတ်နှင့် Owner Info ကို ကြည့်ရှုခြင်း"""
    return await service.get_public_shop_detail(shop_id)


# ==========================================
# OWNER ENDPOINTS
# ==========================================
owner_router = APIRouter(prefix="/owner/shops", tags=["Shop Owner Management"])


@owner_router.post("", response_model=ShopResponse, status_code=status.HTTP_201_CREATED)
async def create_shop_by_owner(
    shop_in: ShopCreate,
    current_user: User = Depends(get_current_active_user),
    service: ShopService = Depends(get_shop_service),
):
    """Owner: Shop အသစ် ဆောက်ခြင်း"""
    return await service.create_shop(owner_id=current_user.id, shop_in=shop_in)


@owner_router.get("", response_model=PaginatedResponse[ShopResponse])
async def list_owner_shops(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    service: ShopService = Depends(get_shop_service),
):
    """Owner: မိမိပိုင်ဆိုင်သော Shop များ စာရင်းကို ကြည့်ရှုခြင်း"""
    return await service.get_owner_shops(
        owner_id=current_user.id, page=page, size=size
    )

@owner_router.get("/{shop_id}", response_model=ShopResponse)
async def get_owner_shop(
    shop_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: ShopService = Depends(get_shop_service),
):
    """Owner: မိမိ Shop အသေးစိတ် ကြည့်ရှုခြင်း"""
    return await service.get_owner_shop_detail(
        shop_id=shop_id, owner_id=current_user.id
    )


@owner_router.patch("/{shop_id}", response_model=ShopResponse)
async def update_owner_shop(
    shop_id: uuid.UUID,
    shop_in: ShopOwnerUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ShopService = Depends(get_shop_service),
):
    """Owner: မိမိ Shop အချက်အလက် ပြင်ဆင်ခြင်း"""
    return await service.update_owner_shop(
        shop_id=shop_id, owner_id=current_user.id, shop_in=shop_in
    )


# ==========================================
# ADMIN ENDPOINTS
# ==========================================
admin_router = APIRouter(prefix="/admin/shops", tags=["Admin Shop Management"])


@admin_router.patch("/{shop_id}/status", response_model=ShopResponse)
async def admin_update_shop_status(
    shop_id: uuid.UUID,
    status_in: ShopAdminStatusUpdate,
    _: User = Depends(has_permission("shops:manage_status")),
    service: ShopService = Depends(get_shop_service),
):
    """Admin: Shop Active/Inactive Status ပြောင်းလဲခြင်း"""
    return await service.admin_update_status(shop_id=shop_id, status_in=status_in)


@admin_router.patch("/{shop_id}/verification", response_model=ShopResponse)
async def admin_update_shop_verification(
    shop_id: uuid.UUID,
    verification_in: ShopAdminVerificationUpdate,
    _: User = Depends(has_permission("shops:manage_verification")),
    service: ShopService = Depends(get_shop_service),
):
    """Admin: Shop Verified/Unverified Status ပြောင်းလဲခြင်း"""
    return await service.admin_update_verification(
        shop_id=shop_id, verification_in=verification_in
    )


@admin_router.delete("/{shop_id}")
async def admin_delete_shop(
    shop_id: uuid.UUID,
    hard_delete: bool = Query(False, description="True ပေးပါက Permanent ဖျက်ပါမည်"),
    _: User = Depends(has_permission("shops:delete")),
    service: ShopService = Depends(get_shop_service),
):
    """Admin: Shop ကို Soft Delete သို့မဟုတ် Hard Delete ပြုလုပ်ခြင်း"""
    return await service.admin_delete_shop(
        shop_id=shop_id, is_hard_delete=hard_delete
    )