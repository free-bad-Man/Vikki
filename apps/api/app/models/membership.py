"""
Модель Membership (членство пользователя в tenant с ролью).

Связующая таблица между User и Role.
Позволяет пользователю иметь разные роли в разных tenant.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Membership(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Таблица: memberships

    Связь пользователя с tenant через роль.
    """
    __tablename__ = "memberships"

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
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    invited_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )
    is_owner: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Владелец tenant (максимальные права)",
    )

    # Отношения
    tenant = relationship("Tenant", back_populates="memberships", lazy="joined")
    user = relationship(
        "User",
        back_populates="memberships",
        lazy="joined",
        foreign_keys=[user_id],
    )
    role = relationship("Role", back_populates="memberships", lazy="joined")
    inviter = relationship(
        "User",
        foreign_keys=[invited_by],
        remote_side="User.id",
        lazy="select",
        viewonly=True,
    )

    # Индексы и ограничения
    __table_args__ = (
        Index("ix_memberships_tenant_id", "tenant_id"),
        Index("ix_memberships_user_id", "user_id"),
        Index("ix_memberships_role_id", "role_id"),
        # Один пользователь может иметь только одно membership в tenant
        UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_user"),
        Index("ix_memberships_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<Membership(id={self.id}, user_id={self.user_id}, tenant_id={self.tenant_id}, role_id={self.role_id})>"
