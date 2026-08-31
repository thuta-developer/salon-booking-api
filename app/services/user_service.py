import uuid
import math
from datetime import datetime, timezone
from typing import Optional, Dict, List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    DUMMY_BCRYPT_HASH,
)
from app.core.token_blacklist import is_token_revoked, revoke_token
from app.models.rbac import Role
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService
from app.schemas.common import PaginatedResponse
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.models.user import User

DEFAULT_REGISTER_ROLE = "Customer"

class UserService(BaseService[User, UserRepository]):

    def __init__(self, user_repository: UserRepository):
        super().__init__(user_repository)
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

        role_stmt = select(Role).where(Role.name == DEFAULT_REGISTER_ROLE)
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
            "roles": role_names
        }

        return UserResponse(**response_dict)

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
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Refresh Token ကို Logout လုပ်ထားလျှင် ငြင်းပယ်မည်
        if await is_token_revoked(payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
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

    async def get_all_users_with_roles(self) -> List[User]:
        stmt = select(User).options(selectinload(User.roles))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_user_with_roles_by_id(self, user_id: uuid.UUID) -> User:
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_users_list(
        self,
        search: Optional[str],
        account_type: Optional[str],
        is_active: Optional[bool],
        page: int,
        size: int,
    ) -> PaginatedResponse[UserResponse]:
        users, total = await self.user_repository.get_paginated_users(
            search=search, account_type=account_type, is_active=is_active, page=page, size=size
        )
        total_pages = math.ceil(total / size) if total > 0 else 0

        items = []
        for u in users:
            role_names = [role.name for role in u.roles] if u.roles else []
            user_res = UserResponse(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                phone_number=u.phone_number,
                account_type=u.account_type,
                is_active=u.is_active,
                is_verified=u.is_verified,
                is_superuser=u.is_superuser,
                last_login=u.last_login,
                created_at=u.created_at,
                updated_at=u.updated_at,
                roles=role_names,
            )
            items.append(user_res)
        return PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

    async def get_user_by_id(self, user_id: uuid.UUID) -> UserResponse:
        user = await self.user_repository.get_by_id_with_relations(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return UserResponse.model_validate(user)

    async def update_user(
        self,
        user_id: uuid.UUID,
        user_in: UserUpdate,
        acting_user: Optional[User] = None,
    ) -> UserResponse:
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # ---- Authorization Guards ----
        update_data = user_in.model_dump(exclude_unset=True)

        if acting_user is not None:
            if user.is_superuser and not acting_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not allowed to modify a superuser account",
                )
            # Privilege escalation ကာကွယ်ရန် — non-superuser က account_type /
            # is_verified (email verify bypass / staff promotion) ကို မပြောင်းနိုင်ပါ
            if not acting_user.is_superuser:
                privileged_fields = {"is_verified", "account_type"}
                if privileged_fields & update_data.keys():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only a superuser can change account_type or verification status",
                    )
            if acting_user.id == user.id and update_data.get("is_active") is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot deactivate your own account",
                )

        if "phone_number" in update_data and update_data["phone_number"]:
            update_data["phone_number"] = update_data["phone_number"].strip()
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now(timezone.utc)
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or phone number already in use",
            )

        role_names = [role.name for role in user.roles] if user.roles else []

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            account_type=user.account_type,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=role_names
        )

    async def _guard_target_user(
        self, target: User, acting_user: Optional[User], action: str
    ) -> None:
        """Deletion/deactivation များတွင် superuser နှင့် self ‌ကို ကာကွယ်ပေးသည်"""
        if acting_user is None:
            return
        if acting_user.id == target.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You cannot {action} your own account",
            )
        if target.is_superuser and not acting_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You are not allowed to {action} a superuser account",
            )

    async def delete_user(
        self, user_id: uuid.UUID, acting_user: Optional[User] = None
    ) -> dict:
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        await self._guard_target_user(user, acting_user, "delete")
        await self.user_repository.hard_delete(user_id)
        return {"message": "User hard deleted successfully"}

    async def soft_delete_user(
        self, user_id: uuid.UUID, acting_user: Optional[User] = None
    ) -> dict:
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        await self._guard_target_user(user, acting_user, "deactivate")
        await self.user_repository.soft_delete(user_id)
        return {"message": "User soft deleted successfully"}




