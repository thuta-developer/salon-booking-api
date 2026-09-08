"""ServiceCategory module ORM models — service categories inside a Shop.

The class is named ``ServiceCategory`` (NOT ``ShopCategory``) — the
``Shop.categories`` relationship in ``app.modules.shop.models`` refers to it
by this name.
"""
import uuid
from typing import Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel

from app.modules.shop.models import Shop

class ServiceCategory(BaseModel):
    __tablename__ = "service_categories"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    shop: Mapped["Shop"] = relationship(
        "Shop",
        back_populates="categories",
        lazy="raise_on_sql",
    )

    __table_args__ = (
        UniqueConstraint("shop_id", "name", name="uq_shop_category_name"),
        Index("ix_service_categories_shop_order", "shop_id", "display_order"),
    )

    def __repr__(self) -> str:
        return f"<ServiceCategory {self.name}> (Shop {self.shop_id})"

__all__ = ["ServiceCategory"]