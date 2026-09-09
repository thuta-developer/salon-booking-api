import uuid

from sqlalchemy import Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel


class BarberService(BaseModel):
    __tablename__ = "barber_services"

    shop_barber_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shop_barbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    service_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships (string-based → resolved at mapper-configuration time)
    barber: Mapped["ShopBarber"] = relationship(
        "ShopBarber",
        back_populates="barber_services",
        lazy="raise_on_sql",
    )
    service: Mapped["Service"] = relationship(
        "Service",
        back_populates="barber_services",
        lazy="raise_on_sql",
    )

    __table_args__ = (
        UniqueConstraint("shop_barber_id", "service_id", name="uq_barber_service"),
        Index("ix_barber_services_barber_service", "shop_barber_id", "service_id"),
    )

    def __repr__(self) -> str:
        return f"<BarberService barber_id={self.shop_barber_id} service_id={self.service_id}>"


# Safe bottom-of-module registration to avoid circular imports
from app.modules.shop_barbers import models as _shop_barbers_models_registry  # noqa: E402,F401
from app.modules.services import models as _services_models_registry  # noqa: E402,F401

__all__ = ["BarberService"]






