"""
Dependencies для аутентификации и авторизации.
"""
from typing import Optional, List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.membership import Membership
from app.models.role import Role
from app.utils.jwt import decode_token
from app.schemas.auth import TokenData


# HTTP Bearer схема
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency для получения текущего пользователя из JWT токена.
    
    Raises:
        HTTPException 401: Если токен отсутствует или невалидный
        HTTPException 404: Если пользователь не найден
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.is_active == True,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user


async def get_tenant_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """
    Dependency для получения tenant контекста текущего пользователя.
    
    Raises:
        HTTPException 404: Если tenant не найден
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == current_user.tenant_id,
            Tenant.deleted_at.is_(None),
        )
    )
    tenant = result.scalar_one_or_none()
    
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    return tenant


async def get_current_user_with_membership(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> Membership:
    """
    Dependency для проверки membership пользователя в tenant.
    
    Возвращает membership если пользователь имеет доступ к tenant.
    
    Raises:
        HTTPException 403: Если пользователь не имеет membership в tenant
    """
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == current_user.id,
            Membership.tenant_id == tenant.id,
            Membership.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this tenant",
        )
    
    return membership


def require_permission(permission: str):
    """
    Factory для создания dependency с проверкой права.
    
    Args:
        permission: Строка права, например "bank_accounts.read", "users.write", "*"
        
    Returns:
        Dependency function для проверки права доступа
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        tenant: Tenant = Depends(get_tenant_context),
        membership: Membership = Depends(get_current_user_with_membership),
        db: AsyncSession = Depends(get_db),
    ) -> Role:
        """
        Проверяет наличие права у роли пользователя.
        
        Raises:
            HTTPException 403: Если у пользователя нет требуемого права
        """
        # Получаем роль
        result = await db.execute(
            select(Role).where(Role.id == membership.role_id)
        )
        role = result.scalar_one_or_none()
        
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role not found",
            )
        
        # Проверяем права
        permissions = role.permissions or []
        
        # "*" даёт все права
        if "*" in permissions:
            return role
        
        # Проверяем конкретное право
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        
        return role
    
    return permission_checker
