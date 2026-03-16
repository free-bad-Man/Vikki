"""
Модель SbisWebhookEvent (события вебхуков СБИС).

Сохраняет все входящие события от СБИС для обработки.
"""
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin


class SbisWebhookEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Таблица: sbis_webhook_events

    Событие вебхука от СБИС.
    """
    __tablename__ = "sbis_webhook_events"

    # Поля
    tenant_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID tenant (nullable для глобальных событий)",
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Тип события СБИС",
    )
    event_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Уникальный ID события от СБИС",
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Полные данные события",
    )
    signature: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Подпись вебхука для верификации",
    )
    processed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Обработано ли событие",
    )
    processing_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Ошибка обработки",
    )

    # Отношения
    tenant = relationship("Tenant", back_populates="sbis_webhook_events", lazy="select")

    # Индексы
    __table_args__ = (
        Index("ix_sbwh_event_type", "event_type"),
        Index("ix_sbwh_processed", "processed"),
        Index("ix_sbwh_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SbisWebhookEvent(id={self.id}, event_type='{self.event_type}', processed={self.processed})>"
