"""Auth module services — authentication flows + RBAC management.

Contains:
    * AuthService         — register / login / refresh (token lifecycle)
    * RoleService         — role CRUD, permission assignment, caching
    * PermissionService   — permission CRUD
"""
import math
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.common.pagination import PaginatedResponse
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.security import (
    DUMMY_BCRYPT_HASH,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.token_blacklist import revoke_token
from app.modules.auth.models import Role
from app.modules.auth.repository import PermissionRepository, RoleRepository
from app.modules.auth.schemas import (
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    RoleAssignPermissions,
    RoleCreate,
    RoleResponse,
    Token,
)
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserResponse

DEFAULT_REGISTER_ROLE = "Customer"


# ==================================================================
# AUTH SERVICE
# ==================================================================
class AuthService:
    """Handles the authentication lifecycle (register, login, refresh)."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.db = user_repository.db

    # ------------------------------------------------------------------
    # Login brute-force protection helpers (Redis backed, fail-open on error)
    # ------------------------------------------------------------------
    def _attempts_key(self, email: str, client_ip: str = "") -> str:
        # IP + email ပေါင်း key — attacker က victim ၏ account ကို ရည်ရွယ်ချက်ရှိရှိ
        # lock လုပ်ရန် (lockout DoS) မလွယ်စေရန်
        return f"login-attempt:{email.lower()}:{client_ip or 'unknown'}"

    async def _is_login_locked(self, email: str, client_ip: str = "") -> bool:
        try:
            redis = get_redis_client()
            count = await redis.get(self._attempts_key(email, client_ip))
            return int(count or 0) >= settings.LOGIN_MAX_ATTEMPTS
        except Exception:
            return False

    async def _record_failed_attempt(self, email: str, client_ip: str = "") -> None:
        try:
            redis = get_redis_client()
            key = self._attempts_key(email, client_ip)
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, settings.LOGIN_LOCKOUT_MINUTES * 60)
        except Exception:
            return None

    async def _reset_failed_attempts(self, email: str, client_ip: str = "") -> None:
        try:
            redis = get_redis_client()
            await redis.delete(self._attempts_key(email, client_ip))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    async def register_user(self, user_in: UserCreate) -> UserResponse:
        if user_in.password != user_in.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match",
            )

        email = user_in.email.strip().lower()
        phone = user_in.phone_number.strip() if user_in.phone_number else None

        if await self.user_repository.exists_by_email_or_phone(email, phone):
            if await self.user_repository.get_by_email(email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already exists",
            )

        user_data = user_in.model_dump(exclude={"password", "confirm_password"})
        user_data["email"] = email
        user_data["phone_number"] = phone
        user_data["hashed_password"] = get_password_hash(user_in.password)

        role_stmt = (
            select(Role)
            .options(noload(Role.permissions))
            .where(Role.name == DEFAULT_REGISTER_ROLE)
        )
        role_result = await self.db.execute(role_stmt)
        customer_role = role_result.scalar_one_or_none()

        user = User(**user_data)
        if customer_role:
            user.roles.append(customer_role)
        self.db.add(user)

        # Concurrent registration အတွက် unique constraint violation ကို
        # clean 400 အဖြစ် ပြန်ပေးရန် (500 crash မဖြစ်စေရန်)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or phone number already exists",
            )

        role_names = [customer_role.name] if customer_role else []

        response_dict = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "account_type": user.account_type,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_superuser": user.is_superuser,
            "last_login": user.last_login,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": role_names,
        }

        return UserResponse(**response_dict)

    # ------------------------------------------------------------------
    # Login & token refresh
    # ------------------------------------------------------------------
    async def login_user(
        self,
        email: str,
        password: str,
        client_ip: Optional[str] = None,
    ) -> Token:
        email = (email or "").strip().lower()

        if await self._is_login_locked(email, client_ip or ""):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again later.",
                headers={"Retry-After": str(settings.LOGIN_LOCKOUT_MINUTES * 60)},
            )

        user = await self.user_repository.get_by_email(email)

        # Timing Attack (User Enumeration) ကာကွယ်ရန် user မရှိလျှင်လည်း
        # dummy hash ကို အမြဲ verify လုပ်သည်။
        hash_to_check = user.hashed_password if user else DUMMY_BCRYPT_HASH
        password_ok = verify_password(password, hash_to_check)

        if not user or not password_ok:
            if user:
                await self._record_failed_attempt(email, client_ip or "")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account",
            )

        await self._reset_failed_attempts(email, client_ip or "")

        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()

        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        payload = decode_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID in token",
            )

        user = await self.user_repository.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        await revoke_token(payload)
        new_access_token = create_access_token(subject=user.id)
        new_refresh_token = create_refresh_token(subject=user.id)
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }


# ==================================================================
# ROLE SERVICE (RBAC)
# ==================================================================
# System အတွက် မရှိမဖြစ် roles — ဒါတွေကို delete/rename လုပ်ခွင့်မပြုပါ
SYSTEM_ROLES = {"Super Admin", "Customer"}

CACHE_TTL = 3600  # 1 hour


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
        await self.db.refresh(
            role, attribute_names=["permissions"]
        )  # Eager Load ဆက်လက်ထိန်းထားနိုင်ရန်

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
        roles, total = await self.role_repo.get_paginated_roles(
            search=search, page=page, size=size
        )
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        role_response = RoleResponse.model_validate(role)
        await self.redis.set(cache_key, role_response.model_dump_json(), ex=CACHE_TTL)

        return role_response

    async def assign_permissions_to_role(
        self, role_id: uuid.UUID, data: RoleAssignPermissions
    ) -> RoleResponse:
        role = await self.role_repo.get_by_id_with_permissions(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        if role.name in SYSTEM_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"System role '{role.name}' cannot be deleted",
            )

        await self.role_repo.delete(role_id)

        # Cache Invalidation ပြုလုပ်ခြင်း
        await self._invalidate_role_caches(role_id=role_id)

        return {"message": "Role deleted successfully"}


# ==================================================================
# PERMISSION SERVICE (RBAC)
# ==================================================================
class PermissionService:
    def __init__(self, db: AsyncSession):
        self.perm_repo = PermissionRepository(db)

    async def create_permission(self, perm_in: PermissionCreate) -> PermissionResponse:
        perm_data = perm_in.model_dump()
        # Leading/trailing whitespace + case-insensitive duplicate ကာကွယ်ရန်
        perm_data["name"] = perm_data["name"].strip()
        if not perm_data["name"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission name is required",
            )

        existing = await self.perm_repo.get_by_name_ci(perm_data["name"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission '{perm_data['name']}' already exists",
            )
        try:
            perm = await self.perm_repo.create(perm_data)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission '{perm_data['name']}' already exists",
            )
        return PermissionResponse.model_validate(perm)

    async def get_permissions_list(
        self, search: Optional[str], module: Optional[str], page: int, size: int
    ) -> PaginatedResponse[PermissionResponse]:
        perms, total = await self.perm_repo.get_paginated_permissions(
            search=search, module=module, page=page, size=size
        )
        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [PermissionResponse.model_validate(p) for p in perms]
        return PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

    async def update_permission(
        self, perm_id: uuid.UUID, perm_in: PermissionUpdate
    ) -> PermissionResponse:
        perm = await self.perm_repo.get_by_id(perm_id)
        if not perm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
            )

        update_data = perm_in.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"]:
            new_name = update_data["name"].strip()
            if not new_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Permission name is required",
                )
            update_data["name"] = new_name
            duplicate = await self.perm_repo.get_by_name_ci(new_name)
            if duplicate and duplicate.id != perm.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Permission name already exists",
                )

        try:
            updated = await self.perm_repo.update(perm, update_data)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission name already exists",
            )
        return PermissionResponse.model_validate(updated)

    async def delete_permission(self, perm_id: uuid.UUID) -> dict:
        success = await self.perm_repo.delete(perm_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
            )
        return {"message": "Permission deleted successfully"}