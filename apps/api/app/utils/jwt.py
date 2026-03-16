"""
JWT утилиты для аутентификации.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

from app.config import settings


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Создаёт JWT access токен.
    
    Args:
        data: Данные для кодирования (обычно {"sub": user_id, "tenant_id": ...})
        expires_delta: Время жизни токена (опционально)
        
    Returns:
        JWT токен в виде строки
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Декодирует JWT токен.
    
    Args:
        token: JWT токен
        
    Returns:
        Раскодированные данные или None если токен невалидный
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None
