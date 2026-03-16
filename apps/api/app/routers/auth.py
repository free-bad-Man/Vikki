"""
Auth router: аутентификация и выдача токенов.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.utils.password import verify_password
from app.utils.jwt import create_access_token
from app.schemas.auth import LoginRequest, TokenResponse, UserSchema
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Аутентификация пользователя и получение JWT токена.
    
    - **email**: Email пользователя
    - **password**: Пароль
    - **tenant_slug**: Slug тенанта для выбора контекста
    """
    # Находим tenant по slug
    result = await db.execute(
        select(Tenant).where(
            Tenant.slug == request.tenant_slug,
            Tenant.deleted_at.is_(None),
        )
    )
    tenant = result.scalar_one_or_none()
    
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    # Находим пользователя в tenant
    result = await db.execute(
        select(User).where(
            User.email == request.email,
            User.tenant_id == tenant.id,
            User.is_active == True,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Проверяем пароль
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Создаём токен
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.id, "tenant_id": tenant.id},
        expires_delta=access_token_expires,
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.get("/me", response_model=UserSchema)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о текущем пользователе.
    
    Требует валидный JWT токен в заголовке Authorization: Bearer <token>
    """
    return current_user
