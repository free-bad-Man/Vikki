"""
Модель AuditLog (аудит событий).

Логирование действий пользователей и системных событий.
"""
from typing import Optional
from sqlalchemy import String, ForeignKey, Index, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Таблица: audit_logs

    Лог аудита событий.
    Примечание: нет SoftDeleteMixin — логи не удаляются.
    tenant_id nullable для глобальных системных событий.
    """
    __tablename__ = "audit_logs"

    # Поля
    # tenant_id nullable — для глобальных системных событий
    tenant_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID пользователя (nullable для системных событий)",
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Тип события: 'user.login', 'document.create', etc.",
    )
    event_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="app",
        comment="Категория: 'auth', 'app', 'system', 'security'",
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Действие: 'create', 'update', 'delete', 'login', 'logout'",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        comment="Статус: 'success' или 'failure'",
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP-адрес (IPv4/IPv6)",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="User-Agent",
    )
    # Ссылка на связанный объект
    related_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Тип объекта: 'User', 'Transaction', 'Document', etc.",
    )
    related_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="ID объекта",
    )
    # Детали события (JSONB)
    payload: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Детали события (старые/новые значения)",
    )
    message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Человекочитаемое описание",
    )

    # Отношения
    tenant = relationship("Tenant", back_populates="audit_logs", lazy="select")
    user = relationship("User", back_populates="audit_logs", lazy="select")

    # Индексы
    __table_args__ = (
        Index("ix_audit_logs_tenant_id", "tenant_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_event_category", "event_category"),
        Index("ix_audit_logs_created_at", "created_at"),
        # Аналитика: tenant + дата + категория
        Index("ix_audit_logs_tenant_category_date", "tenant_id", "event_category", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event='{self.event_type}', action='{self.action}')>"
