import uuid
import math
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.role_repository import RoleRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleResponse, RoleAssignPermissions
from app.schemas.user import UserResponse
from app.models.rbac import Role
from app.models.user import User
from app.core.redis_client import get_redis_client

# System အတွက် မရှိမဖြစ် roles — ဒါတွေကို delete/rename လုပ်ခွင့်မပြုပါ
SYSTEM_ROLES = {"Super Admin", "Customer"}

CACHE_TTL = 3600 # 1 hour

class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.perm_repo = PermissionRepository(db)
        self.user_repo = UserRepository(db)
        self.redis = get_redis_client()

    # --------------------------------------------------------------------------
    # Cache Helper Methods
    # --------------------------------------------------------------------------
    async def _invalidate_role_caches(self, role_id: Optional[uuid.UUID] = None):
        keys_to_delete = []
        if role_id:
            keys_to_delete.append(f"role:{role_id}")

        async for key in self.redis.scan_iter(match="roles:list:*"):
            keys_to_delete.append(key)

        if keys_to_delete:
            await self.redis.delete(*keys_to_delete)

    async def create_role(self, role_in: RoleCreate) -> RoleResponse:
        role_data = role_in.model_dump()
        # Leading/trailing whitespace + case-insensitive duplicate ကာကွယ်ရန်
        role_data["name"] = role_data["name"].strip()
        if not role_data["name"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Role name is required"
            )

        existing = await self.role_repo.get_by_name_ci(role_data["name"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_data['name']}' already exists",
            )

        permission_ids = role_data.pop("permission_ids", [])

        # Role Entity အသစ်တည်ဆောက်ခြင်း
        role = Role(**role_data)

        if permission_ids:
            permissions = await self.perm_repo.get_by_ids(permission_ids)
            if len(permissions) != len(set(permission_ids)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more permissions not found",
                )
            role.permissions = permissions
        else:
            role.permissions = []

        self.db.add(role)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_in.name}' already exists",
            )
        await self.db.refresh(role, attribute_names=["permissions"]) # Eager Load ဆက်လက်ထိန်းထားနိုင်ရန်

        await self._invalidate_role_caches()
        return RoleResponse.model_validate(role)

    async def get_roles_list(
        self, search: Optional[str], page: int, size: int
    ) -> PaginatedResponse[RoleResponse]:
        # Cache Key တည်ဆောက်ခြင်း
        cache_key = f"roles:list:{search or 'all'}:{page}:{size}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return PaginatedResponse[RoleResponse].model_validate_json(cached_data)

        # Cache Miss ဖြစ်ပါက Database မှ ဆွဲယူမည်
        roles, total = await self.role_repo.get_paginated_roles(search=search, page=page, size=size)
        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [RoleResponse.model_validate(r) for r in roles]

        response = PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

        # Redis တွင် သိမ်းဆည်းခြင်း
        await self.redis.set(cache_key, response.model_dump_json(), ex=CACHE_TTL)
        return response

    async def get_role_by_id(self, role_id: uuid.UUID) -> RoleResponse:
        cache_key = f"role:{role_id}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return RoleResponse.model_validate_json(cached_data)

        role = await self.role_repo.get_by_id_with_permissions(role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        role_response = RoleResponse.model_validate(role)
        await self.redis.set(cache_key, role_response.model_dump_json(), ex=CACHE_TTL)

        return role_response

    async def assign_permissions_to_role(
        self, role_id: uuid.UUID, data: RoleAssignPermissions
    ) -> RoleResponse:
        role = await self.role_repo.get_by_id_with_permissions(role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        permissions = await self.perm_repo.get_by_ids(data.permission_ids)
        if len(permissions) != len(set(data.permission_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more permissions not found",
            )

        updated_role = await self.role_repo.update_role_permissions(role, permissions)
        response = RoleResponse.model_validate(updated_role)

        # Role state ပြောင်းသွားသဖြင့် သက်ဆိုင်ရာ Cache များကို ဖျက်မည်
        await self._invalidate_role_caches(role_id=role_id)

        return response

    async def assign_roles_to_user(
        self,
        user_id: uuid.UUID,
        role_ids: List[uuid.UUID],
        acting_user: Optional[User] = None,
    ) -> UserResponse:
        user = await self.user_repo.get_by_id_with_relations(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        roles = await self.role_repo.get_by_ids(role_ids)
        if len(roles) != len(set(role_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more roles not found",
            )

        if acting_user is not None and not acting_user.is_superuser:
            if user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not allowed to change a superuser's roles",
                )
            if any(r.name == "Super Admin" for r in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only a superuser can grant the Super Admin role",
                )

        user.roles = roles
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user, attribute_names=["roles"])

        return UserResponse.model_validate(user)

    async def delete_role(self, role_id: uuid.UUID) -> dict:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if role.name in SYSTEM_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"System role '{role.name}' cannot be deleted",
            )

        await self.role_repo.delete(role_id)

        # Cache Invalidation ပြုလုပ်ခြင်း
        await self._invalidate_role_caches(role_id=role_id)

        return {"message": "Role deleted successfully"}