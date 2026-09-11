import uuid
from datetime import time
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, Time
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel

class BusinessHour(BaseModel):
    __tablename__ = "business_hours"

    shop_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Day of week: 0 = Monday, 6 = Sunday (or 1 = Monday, 7 = Sunday)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    open_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    close_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    # Relationships
    shop: Mapped["Shop"] = relationship(
        "Shop",
        back_populates="business_hours",
        lazy="raise_on_sql",
    )

    __table_args__ = (
        # Shop တစ်ခုအတွင်း နေ့ရက်များ ထပ်မနေစေရန် Composite Unique Index
        Index("ix_business_hours_shop_day", "shop_id", "day_of_week", unique=True),
    )

    def __repr__(self) -> str:
        return f"<BusinessHour shop_id={self.shop_id} day={self.day_of_week} closed={self.is_closed}>"


from app.modules.shop import models as _shop_models_registry  # noqa: E402,F401

__all__ = ["BusinessHour"]