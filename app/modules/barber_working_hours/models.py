import uuid
from datetime import time
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, Time
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel


class BarberWorkingHour(BaseModel):
    __tablename__ = "barber_working_hours"

    shop_barber_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shop_barbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Day of week: 0 = Monday, 6 = Sunday
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    barber: Mapped["ShopBarber"] = relationship(
        "ShopBarber",
        back_populates="working_hours",
        lazy="raise_on_sql",
    )

    __table_args__ = (
        # Barber တစ်ယောက်အတွင်း နေ့ရက်များ ထပ်မနေစေရန် Composite Unique Index
        Index("ix_barber_working_hours_barber_day", "shop_barber_id", "day_of_week", unique=True),
    )

    def __repr__(self) -> str:
        return f"<BarberWorkingHour barber_id={self.shop_barber_id} day={self.day_of_week} active={self.is_active}>"


from app.modules.shop_barbers import models as _shop_barbers_registry  # noqa: E402,F401

__all__ = ["BarberWorkingHour"]