import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_active_user, get_db
from app.modules.categories.schemas import (
    ServiceCategoryCreate,
    ServiceCategoryResponse,
    ServiceCategoryUpdate,
)
from app.modules.categories.service import ServiceCategoryService
from app.modules.users.models import User

# NOTE: `/shops` and `/owner` are relative — app/api/router.py mounts this
# module under /api/v1 (avoiding a duplicated /api/v1/api/v1/... prefix).
public_router = APIRouter(prefix="/shops", tags=["Public - Service Categories"])
owner_router = APIRouter(prefix="/owner", tags=["Shop Owner - Service Categories"])


def get_category_service(db: AsyncSession = Depends(get_db)) -> ServiceCategoryService:
    return ServiceCategoryService(db)


# ==========================================
# PUBLIC ENDPOINTS
# ==========================================

@public_router.get(
    "/{shop_id}/categories",
    response_model=List[ServiceCategoryResponse],
)
async def list_public_categories(
    shop_id: uuid.UUID,
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    service: ServiceCategoryService = Depends(get_category_service),
):
    """Public: Active ဖြစ်သော Category များ စာရင်းကို ကြည့်ရှုခြင်း"""
    return await service.get_public_categories(shop_id=shop_id, is_active=is_active)

@public_router.get(
    "/{shop_id}/categories/{category_id}",
    response_model=ServiceCategoryResponse,
)
async def get_public_category_detail(
    shop_id: uuid.UUID,
    category_id: uuid.UUID,
    service: ServiceCategoryService = Depends(get_category_service),
):
    """Public: Active ဖြစ်သော Category တစ်ခု၏ အသေးစိတ်ကို ကြည့်ရှုခြင်း"""
    return await service.get_public_category_detail(
        shop_id=shop_id, category_id=category_id
    )


# ==========================================
# OWNER ENDPOINTS
# ==========================================

@owner_router.post(
    "/shops/{shop_id}/categories",
    response_model=ServiceCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    shop_id: uuid.UUID,
    cat_in: ServiceCategoryCreate,
    current_user: User = Depends(get_current_active_user),
    service: ServiceCategoryService = Depends(get_category_service),
):
    """Shop Owner: Category အသစ် ဖန်တီးခြင်း"""
    return await service.create_category(
        owner_id=current_user.id, shop_id=shop_id, cat_in=cat_in
    )

@owner_router.get(
    "/shops/{shop_id}/categories",
    response_model=List[ServiceCategoryResponse],
)
async def list_owner_categories(
    shop_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: ServiceCategoryService = Depends(get_category_service),
):
    """Shop Owner: မိမိ Shop ၏ Category အားလုံး (Active/Inactive) ကို ကြည့်ရှုခြင်း"""
    return await service.get_owner_categories(
        owner_id=current_user.id, shop_id=shop_id
    )


@owner_router.get(
    "/categories/{category_id}",
    response_model=ServiceCategoryResponse,
)
async def get_owner_category_detail(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    service: ServiceCategoryService = Depends(get_category_service),
):
    """Shop Owner: Category တစ်ခု၏ အသေးစိတ်ကို ကြည့်ရှုခြင်း"""
    return await service.get_owner_category_detail(
        owner_id=current_user.id, category_id=category_id
    )


@owner_router.patch(
    "/categories/{category_id}",
    response_model=ServiceCategoryResponse,
)
async def update_category(
    category_id: uuid.UUID,
    update_in: ServiceCategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ServiceCategoryService = Depends(get_category_service),
):
    """Shop Owner: Category ပြင်ဆင်ခြင်း"""
    return await service.update_category(
        owner_id=current_user.id, category_id=category_id, update_in=update_in
    )


@owner_router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_category(
    category_id: uuid.UUID,
    hard_delete: bool = Query(False, description="True ပေးပါက Permanent Delete လုပ်ပါမည်"),
    current_user: User = Depends(get_current_active_user),
    service: ServiceCategoryService = Depends(get_category_service),
):
    """Shop Owner: Category ကို Soft/Hard Delete ပြုလုပ်ခြင်း"""
    return await service.delete_category(
        owner_id=current_user.id, category_id=category_id, hard_delete=hard_delete
    )