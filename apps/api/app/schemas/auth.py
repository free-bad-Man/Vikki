"""
Схемы для аутентификации.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# =============================================================================
# Request schemas
# =============================================================================

class LoginRequest(BaseModel):
    """Запрос на получение токена."""
    email: EmailStr
    password: str
    tenant_slug: str


# =============================================================================
# Response schemas
# =============================================================================

class TokenResponse(BaseModel):
    """Ответ с токеном."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # секунды


class UserSchema(BaseModel):
    """Информация о пользователе."""
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    tenant_id: str
    
    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """Данные из токена."""
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    exp: Optional[datetime] = None
