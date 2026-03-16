"""
Модель User (пользователь).

Пользователь принадлежит одному tenant и может иметь membership в нескольких.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Таблица: users

    Пользователь системы. Привязан к одному tenant.
    """
    __tablename__ = "users"

    # Поля
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Отношения
    tenant = relationship("Tenant", back_populates="users", lazy="joined")
    memberships = relationship(
        "Membership",
        back_populates="user",
        lazy="select",
        foreign_keys="Membership.user_id",
    )
    invited_memberships = relationship(
        "Membership",
        lazy="select",
        foreign_keys="Membership.invited_by",
        viewonly=True,
    )
    notifications = relationship("Notification", back_populates="user", lazy="select")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="select")

    # Индексы
    __table_args__ = (
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_email", "email"),
        # Уникальность email в рамках tenant (частичный индекс для soft delete)
        Index("ix_users_tenant_email_unique", "tenant_id", "email", unique=True),
        Index("ix_users_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', tenant_id={self.tenant_id})>"
