"""Shop module ORM models — Shop.

``Shop.owner`` → ``User`` and ``Shop.barbers`` → ``ShopBarber``.  Dependent
model modules are imported at the bottom (safe, since they use a similar
pattern) so mapper configuration always resolves regardless of import order.
"""
import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel

class Shop(BaseModel):
    __tablename__ = "shops"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Address fields
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)

    # Media
    logo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="shops",
        lazy="raise_on_sql",
    )
    barbers: Mapped[List["ShopBarber"]] = relationship(
        "ShopBarber",
        back_populates="shop",
        cascade="all, delete-orphan",
        lazy="raise_on_sql",
    )
    categories: Mapped[List["ServiceCategory"]] = relationship(
        "ServiceCategory",
        back_populates="shop",
        cascade="all, delete-orphan",
        lazy="raise_on_sql",
    )

    __table_args__ = (
        Index("ix_shops_city_country", "city", "country"),
        Index("ix_shops_lat_long", "latitude", "longitude"),
    )

    def __repr__(self) -> str:
        return f"<Shop {self.name} ({self.id})>"


# Register dependent models so mapper configuration works even when this
# module is imported first (safe: only fetches module objects).
from app.modules.users import models as _user_models_registry  # noqa: E402,F401
from app.modules.shop_barbers import models as _shop_barbers_models_registry  # noqa: E402,F401
from app.modules.categories import models as _categories_models_registry


__all__ = ["Shop"]