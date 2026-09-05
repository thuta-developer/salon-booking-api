"""Auth module ORM models — RBAC (Roles, Permissions) + association tables.

NOTE: The User model lives in ``app.modules.users.models``; Role/Permission
belong to the authentication/authorization (RBAC) domain.
"""
from typing import List, Optional

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BaseModel

# ------------------------------------------------------------
# Association tables (many-to-many)
# ------------------------------------------------------------
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Permission(BaseModel):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique key e.g., 'bus:create'",
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    module: Mapped[Optional[str]] = mapped_column(
        String(50),
        index=True,
        nullable=True,
        comment="Group permissions by module e.g., 'Bus', 'Booking'",
    )


class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Role name e.g., 'Counter Staff'",
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    permissions: Mapped[List[Permission]] = relationship(
        secondary=role_permissions,
        lazy="selectin",
    )


__all__ = [
    "Permission",
    "Role",
    "role_permissions",
    "user_roles",
]