"""Users module ORM models — User.

``User.shops`` references ``Shop`` (app.modules.shop) and
``User.barber_profiles`` references ``ShopBarber`` (app.modules.shop_barbers).
Both are imported at runtime so they are ALWAYS registered in SQLAlchemy's
mapper registry before ``User``'s mapper is configured.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel
from app.modules.auth.models import Role, user_roles
from app.modules.shop.models import Shop  # noqa: F401
from app.modules.shop_barbers.models import ShopBarber  # noqa: F401

class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(
        String(20), index=True, nullable=True, unique=True
    )

    account_type: Mapped[str] = mapped_column(
        String(100),
        default="customer",
        nullable=False,
        comment="Account type: customer or staff",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp",
    )

    roles: Mapped[List[Role]] = relationship(
        secondary=user_roles,
        lazy="raise_on_sql",
    )
    shops: Mapped[List[Shop]] = relationship(
        Shop,
        back_populates="owner",
        lazy="raise_on_sql",
    )
    barber_profiles: Mapped[List[ShopBarber]] = relationship(
        ShopBarber,
        back_populates="barber",
        lazy="raise_on_sql",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} full_name={self.full_name}>"


__all__ = ["User"]