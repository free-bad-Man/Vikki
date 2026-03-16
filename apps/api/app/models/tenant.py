"""
Модель Tenant (организация/компания).

Базовая сущность для мульти-тенантной архитектуры.
Все данные пользователя принадлежат конкретному tenant.
"""
from sqlalchemy import String, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Таблица: tenants

    Организация или компания в системе.
    """
    __tablename__ = "tenants"

    # Поля
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    # Отношения
    users = relationship("User", back_populates="tenant", lazy="select")
    memberships = relationship("Membership", back_populates="tenant", lazy="select")
    roles = relationship("Role", back_populates="tenant", lazy="select")
    bank_accounts = relationship("BankAccount", back_populates="tenant", lazy="select")
    transactions = relationship("Transaction", back_populates="tenant", lazy="select")
    edo_documents = relationship("EdoDocument", back_populates="tenant", lazy="select")
    cash_operations = relationship("CashOperation", back_populates="tenant", lazy="select")
    notifications = relationship("Notification", back_populates="tenant", lazy="select")
    audit_logs = relationship("AuditLog", back_populates="tenant", lazy="select")
    sbis_webhook_events = relationship("SbisWebhookEvent", back_populates="tenant", lazy="select")

    # Индексы
    __table_args__ = (
        Index("ix_tenants_slug", "slug"),
        Index("ix_tenants_deleted_at", "deleted_at"),
        # Partial unique index для slug + deleted_at будет в миграции
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}')>"
