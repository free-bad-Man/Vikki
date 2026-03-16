"""
Схемы для СБИС вебхуков.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SbisWebhookPayload(BaseModel):
    """Входящий payload вебхука СБИС."""
    event_id: str = Field(..., description="Уникальный ID события")
    event_type: str = Field(..., description="Тип события")
    tenant_id: Optional[str] = Field(None, description="ID tenant")
    data: Dict[str, Any] = Field(default_factory=dict, description="Данные события")


class SbisWebhookResponse(BaseModel):
    """Ответ на вебхук."""
    status: str = "accepted"
    event_id: str
    message: str = "Event queued for processing"


class SbisWebhookEventSchema(BaseModel):
    """Схема события для API."""
    id: str
    event_type: str
    event_id: str
    tenant_id: Optional[str] = None
    payload: Dict[str, Any]
    processed: bool
    processing_error: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SbisWebhookEventListResponse(BaseModel):
    """Ответ со списком событий."""
    items: list[SbisWebhookEventSchema]
    total: int
