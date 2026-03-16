"""
Схемы для транзакций.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Base schemas
# =============================================================================

class TransactionBase(BaseModel):
    """Базовая схема транзакции."""
    transaction_type: str = Field(..., description="Тип: 'incoming' или 'outgoing'")
    amount: float = Field(..., gt=0, description="Сумма транзакции")
    currency: str = Field(default="RUB", min_length=3, max_length=3, description="Валюта (ISO 4217)")
    occurred_at: datetime = Field(..., description="Дата проведения транзакции")
    counterparty_name: Optional[str] = Field(None, description="Название контрагента")
    counterparty_inn: Optional[str] = Field(None, min_length=10, max_length=12, description="ИНН контрагента")
    counterparty_account: Optional[str] = Field(None, min_length=20, max_length=20, description="Счёт контрагента")
    description: Optional[str] = Field(None, description="Назначение платежа")
    document_number: Optional[str] = Field(None, description="Номер документа")
    external_id: Optional[str] = Field(None, description="Внешний ID транзакции")


class TransactionCreate(TransactionBase):
    """Схема для создания транзакции."""
    bank_account_id: str = Field(..., description="ID банковского счёта")


class TransactionUpdate(BaseModel):
    """Схема для обновления транзакции."""
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    is_processed: Optional[bool] = None


# =============================================================================
# Response schemas
# =============================================================================

class TransactionResponse(TransactionBase):
    """Ответ с информацией о транзакции."""
    id: str
    tenant_id: str
    bank_account_id: str
    fingerprint: Optional[str] = None
    is_processed: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Ответ со списком транзакций."""
    items: list[TransactionResponse]
    total: int


# =============================================================================
# Analytics schemas
# =============================================================================

class TransactionAnalytics(BaseModel):
    """Аналитика по транзакциям."""
    total_income: float = Field(..., description="Общая сумма входящих")
    total_outcome: float = Field(..., description="Общая сумма исходящих")
    income_count: int = Field(..., description="Количество входящих")
    outcome_count: int = Field(..., description="Количество исходящих")
    balance: float = Field(..., description="Сальдо (income - outcome)")


class TransactionByPeriod(BaseModel):
    """Транзакции по периодам."""
    period: str  # например "2026-02"
    income: float
    outcome: float
    count: int
