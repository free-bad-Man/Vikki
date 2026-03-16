"""
Модель BankAccount (банковский счёт).

Счёт организации в банке.
"""
from typing import Optional, List
from sqlalchemy import String, Numeric, ForeignKey, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class BankAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Таблица: bank_accounts

    Банковский счёт tenant.
    """
    __tablename__ = "bank_accounts"

    # Поля
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название счёта (например, 'Основный счёт')",
    )
    account_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Номер счёта (20 цифр)",
    )
    bank_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название банка",
    )
    bank_bik: Mapped[str] = mapped_column(
        String(9),
        nullable=False,
        comment="БИК банка",
    )
    bank_correspondent_account: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Корреспондентский счёт банка",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="RUB",
        comment="Валюта счёта (ISO 4217)",
    )
    balance: Mapped[Optional[float]] = mapped_column(
        Numeric(19, 4),
        nullable=True,
        default=0,
        comment="Текущий баланс",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активен ли счёт",
    )

    # Отношения
    tenant = relationship("Tenant", back_populates="bank_accounts", lazy="joined")
    transactions = relationship("Transaction", back_populates="bank_account", lazy="select")
    edo_documents = relationship("EdoDocument", back_populates="bank_account", lazy="select")
    cash_operations = relationship("CashOperation", back_populates="bank_account", lazy="select")

    # Индексы
    __table_args__ = (
        Index("ix_bank_accounts_tenant_id", "tenant_id"),
        Index("ix_bank_accounts_account_number", "account_number"),
        Index("ix_bank_accounts_tenant_account", "tenant_id", "account_number", unique=True),
        Index("ix_bank_accounts_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<BankAccount(id={self.id}, name='{self.name}', account='{self.account_number}')>"
