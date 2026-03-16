"""
Модель Transaction (банковская транзакция).

Входящие/исходящие платежи по счету.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Index,
    DateTime,
    Text,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Transaction(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Таблица: transactions

    Банковская транзакция (платёж).
    """
    __tablename__ = "transactions"

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    bank_account_id: Mapped[str] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    import_job_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="SET NULL"),
        nullable=True,
        comment="Импорт, из которого была создана транзакция",
    )

    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Тип: 'incoming' или 'outgoing'",
    )
    amount: Mapped[float] = mapped_column(
        Numeric(19, 4),
        nullable=False,
        comment="Сумма транзакции",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="RUB",
        comment="Валюта (ISO 4217)",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Дата проведения транзакции",
    )

    counterparty_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    counterparty_inn: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    counterparty_account: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    fingerprint: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Хэш для дедупликации (заполняется импортёром)",
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Внешний ID транзакции (если банк отдаёт)",
    )

    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tenant = relationship("Tenant", back_populates="transactions", lazy="joined")
    bank_account = relationship("BankAccount", back_populates="transactions", lazy="joined")
    import_job = relationship("ImportJob", back_populates="transactions", lazy="joined")
    edo_documents = relationship("EdoDocument", back_populates="transaction", lazy="select")

    __table_args__ = (
        Index("ix_transactions_tenant_id", "tenant_id"),
        Index("ix_transactions_bank_account_id", "bank_account_id"),
        Index("ix_transactions_import_job_id", "import_job_id"),
        Index("ix_transactions_occurred_at", "occurred_at"),
        Index("ix_transactions_tenant_occurred", "tenant_id", "occurred_at"),
        Index("ix_transactions_deleted_at", "deleted_at"),
        Index("ix_transactions_fingerprint", "fingerprint"),
        Index("ix_transactions_external_id", "external_id"),
        Index("ix_transactions_tenant_type_occurred", "tenant_id", "transaction_type", "occurred_at"),
        Index("ix_transactions_tenant_counterparty_inn", "tenant_id", "counterparty_inn"),
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, amount={self.amount}, type='{self.transaction_type}')>"