import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission, get_current_active_user
from app.models.user import User
from app.repositories.shop_repository import ShopRepository
from app.services.shop_service import ShopService
from app.schemas.shop import ShopCreate, ShopUpdate, ShopResponse, ShopDetailResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/shops", tags=["Shops Management"])


def get_shop_service(db: AsyncSession = Depends(get_db)) -> ShopService:
    return ShopService(ShopRepository(db))


@router.post(
    "/",
    response_model=ShopResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("shop:create"))],
)
async def create_shop(
    shop_in: ShopCreate,
    current_user: User = Depends(get_current_active_user),
    service: ShopService = Depends(get_shop_service),
):
    """
    Shop အသစ်ဖန်တီးခြင်း (shop:create permission လိုအပ်သည်)
    """
    return await service.create_shop(shop_in=shop_in, current_user=current_user)


@router.get(
    "/",
    response_model=PaginatedResponse[ShopResponse],
)
async def list_shops(
    search: Optional[str] = Query(None, description="Search by name or description"),
    city: Optional[str] = Query(None, description="Filter by city"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verified status"),
    owner_id: Optional[uuid.UUID] = Query(None, description="Filter by owner ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    service: ShopService = Depends(get_shop_service),
):
    """
    Shops စာရင်းကို Search/Filter နှင့် Pagination ဖြင့် ရယူခြင်း (Public)
    """
    return await service.get_shops_list(
        search=search,
        city=city,
        is_active=is_active,
        is_verified=is_verified,
        owner_id=owner_id,
        page=page,
        size=size,
    )


@router.get(
    "/{shop_id}",
    response_model=ShopDetailResponse,
)
async def get_shop_detail(
    shop_id: uuid.UUID,
    service: ShopService = Depends(get_shop_service),
):
    """
    Shop အသေးစိတ်ကို ID ဖြင့် ရယူခြင်း (Public)
    """
    return await service.get_shop_detail(shop_id=shop_id)


@router.get(
    "/slug/{slug}",
    response_model=ShopDetailResponse,
)
async def get_shop_by_slug(
    slug: str,
    service: ShopService = Depends(get_shop_service),
):
    """
    Shop အသေးစိတ်ကို Slug ဖြင့် ရယူခြင်း (Public)
    """
    return await service.get_shop_by_slug_detail(slug=slug)


@router.put(
    "/{shop_id}",
    response_model=ShopResponse,
)
async def update_shop(
    shop_id: uuid.UUID,
    shop_in: ShopUpdate,
    current_user: User = Depends(has_permission("shop:update")),
    service: ShopService = Depends(get_shop_service),
):
    """
    Shop အချက်အလက် ပြင်ဆင်ခြင်း (shop:update permission လိုအပ်သည်)
    """
    return await service.update_shop(
        shop_id=shop_id, shop_in=shop_in, current_user=current_user
    )


@router.delete(
    "/{shop_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_shop(
    shop_id: uuid.UUID,
    hard_delete: bool = Query(False, description="Permanently delete (default: soft delete)"),
    current_user: User = Depends(has_permission("shop:delete")),
    service: ShopService = Depends(get_shop_service),
):
    """
    Shop ကို Soft Delete သို့မဟုတ် Hard Delete လုပ်ခြင်း
    """
    if hard_delete:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a superuser can hard-delete a shop",
            )
        return await service.hard_delete_shop(shop_id=shop_id, acting_user=current_user)

    return await service.soft_delete_shop(shop_id=shop_id, acting_user=current_user)