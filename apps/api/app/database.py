from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    create_engine,
    DateTime,
    func,
    Index,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings

# =============================================================================
# Engines: sync (Celery/Alembic) и async (приложение)
# =============================================================================

# Async URL (asyncpg) — как и было
async_engine = create_async_engine(settings.database_url, echo=settings.DEBUG)

# Sync URL (psycopg2) — сначала env override, потом settings
# Важно: sync драйвер должен быть "postgresql://", НЕ "postgresql+asyncpg://"
_env_sync = os.getenv("DATABASE_URL_SYNC")
if _env_sync:
    sync_url = _env_sync
else:
    # settings.database_sync_url должен быть sync-совместимым
    sync_url = settings.database_sync_url

sync_engine = create_engine(sync_url, echo=settings.DEBUG)

async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

sync_session_maker = sessionmaker(
    sync_engine,
    expire_on_commit=False,
)

# =============================================================================
# Base с naming convention для Alembic
# =============================================================================

class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей.
    naming_convention обеспечивает стабильные имена индексов/constraints.
    """
    naming_convention = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }

# =============================================================================
# Mixins
# =============================================================================

class UUIDPrimaryKeyMixin:
    """
    Mixin для первичного ключа типа UUID.
    Требует расширения pgcrypto в Postgres.
    """
    id: Mapped[str] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """Mixin для created_at / updated_at."""
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


class SoftDeleteMixin:
    """Mixin для soft delete (deleted_at)."""
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


class TenantScopedMixin:
    """
    Mixin для tenant-scoped таблиц.
    Добавляет tenant_id и индекс по нему.
    """
    tenant_id: Mapped[str] = mapped_column(
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_%(table_name)s_tenant_id", "tenant_id"),
    )

# =============================================================================
# Dependency для получения сессии БД
# =============================================================================

async def get_db() -> AsyncSession:
    """
    FastAPI dependency для получения async сессии.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()