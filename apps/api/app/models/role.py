"""
Модель Role (роль).

Определяет роли пользователей в системе (admin, manager, viewer, etc.).
"""
from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Таблица: roles

    Роль с набором permissions.
    """
    __tablename__ = "roles"

    # Поля
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    # JSONB с permissions: ["bank_accounts.read", "bank_accounts.write", ...]
    permissions: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    is_system: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Системные роли нельзя удалять/редактировать",
    )

    # Отношения
    tenant = relationship("Tenant", back_populates="roles", lazy="joined")
    memberships = relationship("Membership", back_populates="role", lazy="select")

    # Индексы
    __table_args__ = (
        Index("ix_roles_tenant_id", "tenant_id"),
        Index("ix_roles_code", "code"),
        Index("ix_roles_tenant_code_unique", "tenant_id", "code", unique=True),
        Index("ix_roles_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', code='{self.code}')>"
