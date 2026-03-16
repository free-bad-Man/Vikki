"""
Модель EdoDocument (документ электронного документооборота).

Счета, акты, накладные и другие документы.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, ForeignKey, Index, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class EdoDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Таблица: edo_documents

    Документ ЭДО (счёт, акт, накладная, УПД и т.д.).
    """
    __tablename__ = "edo_documents"

    # Поля
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Тип: 'invoice', 'act', 'waybill', 'upd', etc.",
    )
    document_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Номер документа",
    )
    document_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Дата документа",
    )
    amount: Mapped[Optional[float]] = mapped_column(
        Numeric(19, 4),
        nullable=True,
        comment="Сумма документа",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="RUB",
    )
    counterparty_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Название контрагента",
    )
    counterparty_inn: Mapped[Optional[str]] = mapped_column(
        String(12),
        nullable=True,
        comment="ИНН контрагента",
    )
    # Статусы
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        comment="Статус: draft, sent, signed, rejected, cancelled",
    )
    is_signed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    # Ссылка на связанный счёт (опционально)
    bank_account_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Ссылка на транзакцию (опционально)
    transaction_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Метаданные (JSONB)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Отношения
    tenant = relationship("Tenant", back_populates="edo_documents", lazy="joined")
    bank_account = relationship("BankAccount", back_populates="edo_documents", lazy="select")
    transaction = relationship("Transaction", back_populates="edo_documents", lazy="select")

    # Индексы
    __table_args__ = (
        Index("ix_edo_documents_tenant_id", "tenant_id"),
        Index("ix_edo_documents_tenant_number", "tenant_id", "document_number", unique=True),
        Index("ix_edo_documents_document_date", "document_date"),
        Index("ix_edo_documents_tenant_date", "tenant_id", "document_date"),
        Index("ix_edo_documents_status", "status"),
        Index("ix_edo_documents_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<EdoDocument(id={self.id}, type='{self.document_type}', number='{self.document_number}')>"
