"""
Notifications router.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.user import User
from app.dependencies.auth import get_current_user, get_tenant_context
from app.schemas.notification import NotificationResponse, NotificationListResponse, NotificationUpdate


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    is_read: Optional[bool] = Query(None, description="Фильтр по статусу прочтения"),
    limit: int = Query(20, ge=1, le=100, description="Лимит записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список уведомлений текущего пользователя.
    """
    # Базовый запрос
    query = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.deleted_at.is_(None),
    )
    
    # Фильтр по статусу
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    
    # Считаем общее количество
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Применяем лимиты
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить информацию об уведомлении.
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.deleted_at.is_(None),
        )
    )
    notification = result.scalar_one_or_none()
    
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    
    return NotificationResponse.model_validate(notification)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Отметить уведомление как прочитанное.
    """
    from sqlalchemy import func as sql_func
    
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.deleted_at.is_(None),
        )
    )
    notification = result.scalar_one_or_none()
    
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    
    notification.is_read = True
    notification.read_at = sql_func.now()
    
    await db.commit()
    await db.refresh(notification)
    
    return NotificationResponse.model_validate(notification)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить уведомление (soft delete).
    """
    from sqlalchemy import func as sql_func
    
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.deleted_at.is_(None),
        )
    )
    notification = result.scalar_one_or_none()
    
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    
    notification.deleted_at = sql_func.now()
    
    await db.commit()
