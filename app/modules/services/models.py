"""Service module ORM models — services offered by a Shop within a category.

Import note: relationships to other models use string names resolved at
mapper-configuration time.  The dependent model modules are registered with
safe bottom-of-module imports, so there is no circular import no matter which
model module is loaded first (e.g. `services.models` ↔ `categories.models`).
"""
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel


class Service(BaseModel):
    __tablename__ = "services"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships (string-based → resolved at mapper-configuration time)
    shop: Mapped["Shop"] = relationship(
        "Shop",
        back_populates="services",
        lazy="raise_on_sql",
    )
    # NOTE: attribute is `category` (singular) — matches `category_id`, the
    # `ServiceDetailResponse.category` schema field, and the back_populates
    # on `ServiceCategory.services`.
    category: Mapped["ServiceCategory"] = relationship(
        "ServiceCategory",
        back_populates="services",
        lazy="raise_on_sql",
    )

    __table_args__ = (
        UniqueConstraint("shop_id", "name", name="uq_shop_service_name"),
        Index("ix_services_shop_category", "shop_id", "category_id"),
    )

    def __repr__(self) -> str:
        return f"<Service {self.name} - ${self.price} ({self.duration_minutes} mins)>"


# Safe bottom-of-module registration — these statements only fetch the module
# objects into sys.modules (no attribute access at import time), which registers
# the mappers and avoids the services ↔ categories circular import.
from app.modules.shop import models as _shop_models_registry  # noqa: E402,F401
from app.modules.categories import models as _categories_models_registry  # noqa: E402,F401


__all__ = ["Service"]