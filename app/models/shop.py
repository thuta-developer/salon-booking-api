import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


if TYPE_CHECKING:
    from app.models.user import User


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
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )

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
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_shops_city_country", "city", "country"),
        Index("ix_shops_lat_long", "latitude", "longitude"),
    )

    def __repr__(self) -> str:
        return f"<Shop {self.name} ({self.id})>"
