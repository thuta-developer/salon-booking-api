import uuid
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


# ------------------------------------------------------------
# SQLAlchemy Declarative Base — အားလုံးသော ORM Models များ၏ အခြေခံ
# ------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        object_id = self.__dict__.get("id", "<expired>")
        return f"<{self.__class__.__name__}(id={object_id})>"


engine = create_async_engine(
    settings.DATABASE_URL,
    # echo ကို engine အဆင့်မှာ မသုံးတော့ပါ — raw SQL ကို သန့်သန့်ရှင်းရှင်းပြရန်
    # `sqlalchemy.engine` logger ကို app/core/logging.py တွင် ထိန်းချုပ်ထားသည်
    # (DEBUG mode တွင် SQL စာကြောင်းသက်သက်သာ ပေါ်ပါမည်)
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

async_session_factory = AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
