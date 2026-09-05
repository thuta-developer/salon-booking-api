"""Auth module dependency providers (service factories)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.repository import PermissionRepository, RoleRepository
from app.modules.auth.service import AuthService, PermissionService, RoleService
from app.modules.users.repository import UserRepository


def get_auth_service(
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    """AuthService depends on UserRepository (user lookup + persistence)."""
    return AuthService(UserRepository(db))


def get_role_service(db: AsyncSession = Depends(get_db)) -> RoleService:
    return RoleService(db)


def get_permission_service(
    db: AsyncSession = Depends(get_db),
) -> PermissionService:
    return PermissionService(db)