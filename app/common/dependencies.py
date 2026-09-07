"""Shared FastAPI dependencies (auth guards) used across modules."""
import json
import uuid
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import get_redis_client
from app.core.security import decode_token
from app.core.token_blacklist import is_token_revoked
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

# Swagger UI အတွက် OAuth2 Password Bearer Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

USER_CACHE_TTL = 300  # 5 minutes cache TTL


async def invalidate_user_auth_cache(user_id: uuid.UUID | str) -> None:
    """
    User ၏ Status၊ Roles သို့မဟုတ် Permissions ပြောင်းလဲပါက 
    Auth Cache ကို ဖျက်ပေးသည့် Helper Function
    """
    try:
        redis = get_redis_client()
        await redis.delete(f"user:auth:{user_id}")
    except Exception:
        pass


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    JWT Token ကို စစ်ဆေးပြီး Redis Cache မှ User Data ကို ခေါ်ယူသည်။
    Cache Miss ဖြစ်ပါက Database မှ ဆွဲယူပြီး Cache သို့ သိမ်းဆည်းသည်။
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    # Token ကို Blacklist ထဲတွင် ရှိမရှိ စစ်ဆေးခြင်း
    if await is_token_revoked(payload):
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    redis = get_redis_client()
    cache_key = f"user:auth:{user_id_str}"

    # 1. Redis Cache တွင် စစ်ဆေးခြင်း
    try:
        cached_user = await redis.get(cache_key)
        if cached_user:
            user_data = json.loads(cached_user)
            user = User(
                id=uuid.UUID(user_data["id"]),
                email=user_data["email"],
                is_active=user_data["is_active"],
                is_superuser=user_data["is_superuser"],
            )
            # Lightweight set အဖြစ် Permission များကို သိမ်းဆည်းမည်
            user._cached_permissions = set(user_data.get("permissions", []))
            return user
    except Exception:
        pass  # Redis Exception ဖြစ်ပါက DB Fallback သို့ သွားမည်

    # 2. Cache Miss ဖြစ်ပါက DB မှ ဆွဲယူမည်
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id_with_relations(user_id)

    if user is None:
        raise credentials_exception

    # Permissions များကို Extract လုပ်ခြင်း
    user_perms = set()
    for role in user.roles:
        for perm in role.permissions:
            user_perms.add(perm.name)

    user._cached_permissions = user_perms

    # 3. Redis ထဲသို့ Cache ရေးသွင်းခြင်း
    cache_payload = {
        "id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "permissions": list(user_perms),
    }
    try:
        await redis.set(cache_key, json.dumps(cache_payload), ex=USER_CACHE_TTL)
    except Exception:
        pass

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """User Account သည် Active ဖြစ်မဖြစ် စစ်ဆေးပေးသည်။"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )
    return current_user


def has_permission(required_permission: str) -> Callable:
    """
    Dynamic RBAC Permission Guard Dependency Factory
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        # Super Admin သည် Permission အားလုံး ရရှိသည်
        if getattr(current_user, "is_superuser", False):
            return current_user

        # Cache မှ ရသော permissions သို့မဟုတ် ORM relationship မှ ရသော permissions ကို သုံးမည်
        if hasattr(current_user, "_cached_permissions"):
            user_permissions = current_user._cached_permissions
        else:
            user_permissions = set()
            for role in current_user.roles:
                for perm in role.permissions:
                    user_permissions.add(perm.name)

        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required to perform this action",
            )
        return current_user

    return permission_checker