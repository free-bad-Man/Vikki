"""
Схемы для уведомлений.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """Ответ с информацией об уведомлении."""
    id: str
    tenant_id: str
    user_id: str
    title: str
    message: str
    notification_type: str
    is_read: bool
    read_at: Optional[datetime] = None
    payload: Optional[Dict[str, Any]] = None
    related_type: Optional[str] = None
    related_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Ответ со списком уведомлений."""
    items: list[NotificationResponse]
    total: int
    unread_count: Optional[int] = None


class NotificationUpdate(BaseModel):
    """Схема для обновления уведомления."""
    is_read: Optional[bool] = None
