"""
Модель CashOperation (кассовая операция).

Приходные/расходные кассовые ордера.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, ForeignKey, Index, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class CashOperation(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Таблица: cash_operations

    Кассовая операция (ПКО/РКО).
    """
    __tablename__ = "cash_operations"

    # Поля
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operation_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Тип: 'income' (ПКО) или 'expense' (РКО)",
    )
    document_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Номер ордера",
    )
    document_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Дата ордера",
    )
    amount: Mapped[float] = mapped_column(
        Numeric(19, 4),
        nullable=False,
        comment="Сумма операции",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="RUB",
    )
    counterparty_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="ФИО или название контрагента",
    )
    counterparty_inn: Mapped[Optional[str]] = mapped_column(
        String(12),
        nullable=True,
        comment="ИНН контрагента",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Основание операции",
    )
    # Связь с банком (если снятие/внесение на счёт)
    bank_account_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Проведена ли операция",
    )

    # Отношения
    tenant = relationship("Tenant", back_populates="cash_operations", lazy="joined")
    bank_account = relationship("BankAccount", back_populates="cash_operations", lazy="select")

    # Индексы
    __table_args__ = (
        Index("ix_cash_operations_tenant_id", "tenant_id"),
        Index("ix_cash_operations_tenant_number", "tenant_id", "document_number", unique=True),
        Index("ix_cash_operations_document_date", "document_date"),
        Index("ix_cash_operations_tenant_date", "tenant_id", "document_date"),
        Index("ix_cash_operations_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<CashOperation(id={self.id}, type='{self.operation_type}', number='{self.document_number}')>"
