import uuid
import math
from datetime import datetime, timezone
from typing import Optional, Dict, List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
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

    async def register_user(self, user_in: UserCreate) -> UserResponse:
        if user_in.password != user_in.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match",
            )

        if await self.user_repository.exists_by_email_or_phone(
            user_in.email, user_in.phone_number
        ):
            if await self.user_repository.get_by_email(user_in.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already exists",
            )

        user_data = user_in.model_dump(exclude={"password", "confirm_password"})
        user_data["hashed_password"] = get_password_hash(user_in.password)

        role_stmt = select(Role).where(Role.name == DEFAULT_REGISTER_ROLE)
        role_result = await self.db.execute(role_stmt)
        customer_role = role_result.scalar_one_or_none()

        user = User(**user_data)
        if customer_role:
            user.roles.append(customer_role)
        self.db.add(user)
        await self.db.commit()

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

    async def login_user(self, email: str, password: str) -> Token:
        user = await self.user_repository.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account",
            )

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

    async def update_user(self, user_id: uuid.UUID, user_in: UserUpdate) -> UserResponse:
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

        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.commit()

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

    async def delete_user(self, user_id: uuid.UUID) -> dict:
        success = await self.user_repository.hard_delete(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

    async def soft_delete_user(self, user_id: uuid.UUID) -> dict:
        success = await self.user_repository.soft_delete(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )




