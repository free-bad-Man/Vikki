"""
Схемы для кассовых операций.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Base schemas
# =============================================================================

class CashOperationBase(BaseModel):
    """Базовая схема кассовой операции."""
    operation_type: str = Field(..., description="Тип: income (ПКО) или expense (РКО)")
    document_number: str = Field(..., description="Номер ордера")
    document_date: datetime = Field(..., description="Дата ордера")
    amount: float = Field(..., gt=0, description="Сумма операции")
    currency: str = Field(default="RUB", min_length=3, max_length=3, description="Валюта")
    counterparty_name: Optional[str] = Field(None, description="ФИО или название контрагента")
    counterparty_inn: Optional[str] = Field(None, min_length=10, max_length=12, description="ИНН контрагента")
    description: Optional[str] = Field(None, description="Основание операции")


class CashOperationCreate(CashOperationBase):
    """Схема для создания кассовой операции."""
    bank_account_id: Optional[str] = Field(None, description="ID банковского счёта (если снятие/внесение)")


class CashOperationUpdate(BaseModel):
    """Схема для обновления кассовой операции."""
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    is_completed: Optional[bool] = None


# =============================================================================
# Response schemas
# =============================================================================

class CashOperationResponse(CashOperationBase):
    """Ответ с информацией о кассовой операции."""
    id: str
    tenant_id: str
    bank_account_id: Optional[str] = None
    is_completed: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CashOperationListResponse(BaseModel):
    """Ответ со списком кассовых операций."""
    items: list[CashOperationResponse]
    total: int
