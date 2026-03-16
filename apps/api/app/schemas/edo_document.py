"""
Схемы для документов ЭДО.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Base schemas
# =============================================================================

class EdoDocumentBase(BaseModel):
    """Базовая схема документа."""
    document_type: str = Field(..., description="Тип: invoice, act, waybill, upd")
    document_number: str = Field(..., description="Номер документа")
    document_date: datetime = Field(..., description="Дата документа")
    amount: Optional[float] = Field(None, ge=0, description="Сумма документа")
    currency: str = Field(default="RUB", min_length=3, max_length=3, description="Валюта")
    counterparty_name: Optional[str] = Field(None, description="Название контрагента")
    counterparty_inn: Optional[str] = Field(None, min_length=10, max_length=12, description="ИНН контрагента")
    status: str = Field(default="draft", description="Статус: draft, sent, signed, rejected, cancelled")
    description: Optional[str] = Field(None, description="Описание")


class EdoDocumentCreate(EdoDocumentBase):
    """Схема для создания документа."""
    bank_account_id: Optional[str] = Field(None, description="ID банковского счёта")
    transaction_id: Optional[str] = Field(None, description="ID транзакции")


class EdoDocumentUpdate(BaseModel):
    """Схема для обновления документа."""
    amount: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    is_signed: Optional[bool] = None
    description: Optional[str] = None
    metadata_: Optional[dict] = Field(None, alias="metadata")


# =============================================================================
# Response schemas
# =============================================================================

class EdoDocumentResponse(EdoDocumentBase):
    """Ответ с информацией о документе."""
    id: str
    tenant_id: str
    bank_account_id: Optional[str] = None
    transaction_id: Optional[str] = None
    is_signed: bool
    metadata_: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EdoDocumentListResponse(BaseModel):
    """Ответ со списком документов."""
    items: list[EdoDocumentResponse]
    total: int
