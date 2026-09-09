import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.common.dependencies import get_current_active_user, get_db
from app.modules.services.schemas import (
    ServiceCreate,
    ServiceDetailResponse,
    ServiceResponse,
    ServiceUpdate,
)
from app.modules.services.service import ServiceService
from app.modules.users.models import User

public_router = APIRouter(prefix="/shops", tags=["Public - Services"])
owner_router = APIRouter(prefix="/owner", tags=["Shop Owner - Services"])

def get_service_service(db: AsyncSession = Depends(get_db)):
    return ServiceService(db=db)


# ==========================================
# PUBLIC ENDPOINTS
# ==========================================

@public_router.get(
    "/{shop_id}/services",
    response_model=List[ServiceDetailResponse],
)
async def list_public_services(
    shop_id: uuid.UUID,
    category_id: Optional[uuid.UUID] = Query(None, description="Category id filter"),
    is_active: Optional[bool] = Query(None, description="Is active filter"),
    service: ServiceService = Depends(get_service_service),
):
    """Public: Shop တစ်ခု၏ Active ဖြစ်သော Service များကို Category Filter ပါဝင်စွာ ကြည့်ရှုခြင်း"""
    return await service.get_public_services(shop_id=shop_id, category_id=category_id, is_active=is_active)


@public_router.get(
    "/{shop_id}/services/{service_id}",
    response_model=ServiceDetailResponse,
)
async def get_public_service_detail(
    shop_id: uuid.UUID,
    service_id: uuid.UUID,
    service: ServiceService = Depends(get_service_service),
):
    """Public: Service တစ်ခု၏ အသေးစိတ်ကို Category အချက်အလက်ပါ ပူးတွဲကြည့်ရှုခြင်း"""
    return await service.get_public_service_detail(
        shop_id=shop_id, service_id=service_id
    )


# ==========================================
# OWNER ENDPOINTS
# ==========================================

@owner_router.post(
    "/shops/{shop_id}/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service(
    shop_id: uuid.UUID,
    service_in: ServiceCreate,
    current_user: User = Depends(get_current_active_user),
    service: ServiceService = Depends(get_service_service),
):
    """Shop Owner: Service အသစ် ဖန်တီးခြင်း"""
    return await service.create_service(
        owner_id=current_user.id, shop_id=shop_id, service_in=service_in
    )


@owner_router.patch(
    "/services/{service_id}",
    response_model=ServiceResponse,
)
async def update_service(
    service_id: uuid.UUID,
    update_in: ServiceUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ServiceService = Depends(get_service_service),
):
    """Shop Owner: Service အချက်အလက်များကို ပြင်ဆင်ခြင်း"""
    return await service.update_service(
        owner_id=current_user.id, service_id=service_id, update_in=update_in
    )


@owner_router.delete(
    "/services/{service_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_service(
    service_id: uuid.UUID,
    hard_delete: bool = Query(
        False, description="True ပေးပါက Permanent Delete လုပ်ပါမည်"
    ),
    current_user: User = Depends(get_current_active_user),
    service: ServiceService = Depends(get_service_service),
):
    """Shop Owner: Service ကို Soft/Hard Delete ပြုလုပ်ခြင်း"""
    return await service.delete_service(
        owner_id=current_user.id, service_id=service_id, hard_delete=hard_delete
    )

























