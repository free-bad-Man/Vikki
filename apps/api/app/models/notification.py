"""
Модель Notification (уведомление).

Внутренние уведомления для пользователей.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, Index, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Таблица: notifications

    Уведомление для пользователя.
    """
    __tablename__ = "notifications"

    # Поля
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Тип: 'info', 'warning', 'error', 'success'",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Дополнительные данные (JSONB)
    payload: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    # Ссылка на связанный объект (опционально)
    related_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Тип связанного объекта: 'transaction', 'document', etc.",
    )
    related_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="ID связанного объекта",
    )

    # Отношения
    tenant = relationship("Tenant", back_populates="notifications", lazy="joined")
    user = relationship("User", back_populates="notifications", lazy="joined")

    # Индексы
    __table_args__ = (
        Index("ix_notifications_tenant_id", "tenant_id"),
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, title='{self.title}', user_id={self.user_id})>"
