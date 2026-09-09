"""ShopBarber module ORM models — barbers working at a shop.

``ShopBarber.shop`` → ``Shop`` and ``ShopBarber.barber`` → ``User``;
``ShopBarber.barber_services`` → ``BarberService`` (app.modules.barber_services).
All dependent models are imported at the bottom of this module (safe mild
circular) so mapper configuration resolves regardless of import order.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel

class ShopBarber(BaseModel):
    __tablename__ = "shop_barbers"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    barber_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp",
    )

    shop: Mapped["Shop"] = relationship(
        "Shop",
        back_populates="barbers",
        lazy="raise_on_sql",
    )
    barber: Mapped["User"] = relationship(
        "User",
        lazy="raise_on_sql",
    )
    barber_services: Mapped[List["BarberService"]] = relationship(
        "BarberService",
        back_populates="barber",
        cascade="all, delete-orphan",
        lazy="raise_on_sql",
    )

    __table_args__ = (
        UniqueConstraint("shop_id", "barber_id", name="uq_shop_barber"),
        Index("ix_shop_barbers_shop_active", "shop_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<ShopBarber {self.display_name} (Shop: {self.shop_id})>"


# Register dependent models (safe mild circular imports at bottom of module) —
# see shop/models.py note for the same pattern.
from app.modules.shop import models as _shop_models_registry  # noqa: E402,F401
from app.modules.users import models as _user_models_registry  # noqa: E402,F401
from app.modules.barber_services import models as _barber_services_models_registry  # noqa: E402,F401


__all__ = ["ShopBarber"]
