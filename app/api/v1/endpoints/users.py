import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserResponse, UserUpdate, UserWithRolesResponse
from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/users", tags=["Users Management"])


@router.get(
    "/",
    response_model=PaginatedResponse[UserResponse],
    dependencies=[Depends(has_permission("user:read"))],
)
async def list_users(
    search: Optional[str] = Query(None, description="Search by Name, Email, or Phone"),
    account_type: Optional[str] = Query(None, description="Filter by customer or staff"),
    is_active: Optional[bool] = Query(None, description="Filter active/inactive"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search, Filter & Paginated User List API
    """
    service = UserService(UserRepository(db))
    return await service.get_users_list(
        search=search,
        account_type=account_type,
        is_active=is_active,
        page=page,
        size=size,
    )


@router.get(
    "/{user_id}",
    response_model=UserWithRolesResponse,
    dependencies=[Depends(has_permission("user:read"))],
)
async def get_user_detail(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Get Single User Detail by ID
    """
    service = UserService(UserRepository(db))
    user = await service.get_user_with_roles_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
)
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: User = Depends(has_permission("user:update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update User Information
    """
    service = UserService(UserRepository(db))
    return await service.update_user(user_id, user_in, acting_user=current_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_user(
    user_id: uuid.UUID,
    hard_delete: bool = Query(False, description="Permanently delete (default: soft delete)"),
    current_user: User = Depends(has_permission("user:delete")),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete User by ID
    """
    service = UserService(UserRepository(db))
    if hard_delete:
        # Irreversible operation — superuser သာ လုပ်နိုင်သည်
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a superuser can hard-delete a user",
            )
        await service.delete_user(user_id, acting_user=current_user)
        return {"message": "User hard deleted successfully"}

    await service.soft_delete_user(user_id, acting_user=current_user)
    return {"message": "User soft deleted successfully"}

    