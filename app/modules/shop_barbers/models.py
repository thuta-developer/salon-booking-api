import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text, DateTime, UniqueConstraint
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.shop.models import Shop


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

    __table_args__ = (
        UniqueConstraint("shop_id", "barber_id", name="uq_shop_barber"),
        Index("ix_shop_barbers_shop_active", "shop_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<ShopBarber {self.display_name} (Shop: {self.shop_id})>"


__all__ = ["ShopBarber"]
