"""
Схемы для банковских счетов.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Base schemas
# =============================================================================

class BankAccountBase(BaseModel):
    """Базовая схема счёта."""
    name: str = Field(..., description="Название счёта")
    account_number: str = Field(..., min_length=20, max_length=20, description="Номер счёта (20 цифр)")
    bank_name: str = Field(..., description="Название банка")
    bank_bik: str = Field(..., min_length=9, max_length=9, description="БИК банка")
    bank_correspondent_account: Optional[str] = Field(None, description="Корреспондентский счёт банка")
    currency: str = Field(default="RUB", min_length=3, max_length=3, description="Валюта (ISO 4217)")


class BankAccountCreate(BankAccountBase):
    """Схема для создания счёта."""
    pass


class BankAccountUpdate(BaseModel):
    """Схема для обновления счёта."""
    name: Optional[str] = None
    bank_name: Optional[str] = None
    bank_bik: Optional[str] = None
    bank_correspondent_account: Optional[str] = None
    is_active: Optional[bool] = None


# =============================================================================
# Response schemas
# =============================================================================

class BankAccountResponse(BankAccountBase):
    """Ответ с информацией о счёте."""
    id: str
    tenant_id: str
    balance: Optional[float] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BankAccountListResponse(BaseModel):
    """Ответ со списком счетов."""
    items: list[BankAccountResponse]
    total: int
