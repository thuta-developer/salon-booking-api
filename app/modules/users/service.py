"""Users module service — user account management (CRUD).

Authentication flows (register / login / refresh) live in
``app.modules.auth.service.AuthService``.
"""
import math
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.common.pagination import PaginatedResponse
from app.common.service import BaseService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserResponse, UserUpdate


class UserService(BaseService[User, UserRepository]):
    def __init__(self, user_repository: UserRepository):
        super().__init__(user_repository)
        self.user_repository = user_repository
        self.db = user_repository.db

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
            search=search,
            account_type=account_type,
            is_active=is_active,
            page=page,
            size=size,
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
            roles=role_names,
        )

    async def _guard_target_user(
        self, target: User, acting_user: Optional[User], action: str
    ) -> None:
        """Deletion/deactivation များတွင် superuser နှင့် self ကို ကာကွယ်ပေးသည်"""
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