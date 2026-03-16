"""
Webhook router для СБИС.

Принимает события от СБИС и сохраняет их для последующей обработки.
"""
import hashlib
import hmac
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.sbis_webhook_event import SbisWebhookEvent
from app.schemas.sbis_webhook import (
    SbisWebhookPayload,
    SbisWebhookResponse,
    SbisWebhookEventSchema,
    SbisWebhookEventListResponse,
)
from app.dependencies.auth import get_current_user, require_permission


router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Секрет для верификации вебхуков (должен быть в .env)
SBIS_WEBHOOK_SECRET = os.getenv("SBIS_WEBHOOK_SECRET", "dev-secret")


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Проверяет подпись вебхука.

    СБИС отправляет подпись в заголовке X-Sbis-Signature.
    """
    if not signature:
        return False

    expected_signature = hmac.new(
        SBIS_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


@router.post("/sbis", response_model=SbisWebhookResponse, status_code=status.HTTP_202_ACCEPTED)
async def sbis_webhook(
    request: Request,
    x_sbis_signature: Optional[str] = Header(None, alias="X-Sbis-Signature"),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db),
):
    """
    Вебхук для получения событий от СБИС.

    Принимает события и ставит их в очередь на обработку.

    DEV-режим: если tenant_id нет в body, можно передать его в заголовке X-Tenant-Id.
    """
    body = await request.body()

    # Верификация подписи (в production должна быть включена)
    if os.getenv("SBIS_VERIFY_WEBHOOK", "false").lower() == "true":
        if not x_sbis_signature or not verify_webhook_signature(body, x_sbis_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

    # Парсим payload
    try:
        import json

        data = json.loads(body)
        payload = SbisWebhookPayload(**data)
    except (json.JSONDecodeError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}",
        )

    # Определяем tenant_id: body -> header -> error
    tenant_id = getattr(payload, "tenant_id", None) or x_tenant_id
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required for SBIS webhook (body.tenant_id or header X-Tenant-Id)",
        )

    # Проверяем не дубликат ли это
    existing = await db.execute(
        select(SbisWebhookEvent).where(SbisWebhookEvent.event_id == payload.event_id)
    )
    if existing.scalar_one_or_none() is not None:
        return SbisWebhookResponse(
            status="duplicate",
            event_id=payload.event_id,
            message="Event already received",
        )

    # Сохраняем событие
    event = SbisWebhookEvent(
        tenant_id=tenant_id,
        event_type=payload.event_type,
        event_id=payload.event_id,
        payload=payload.data,
        signature=x_sbis_signature,
        processed=False,
    )

    db.add(event)
    await db.commit()

    # Отправляем в Celery для асинхронной обработки
    from app.tasks.sbis import process_sbwebhook_event

    process_sbwebhook_event.delay(str(event.id))

    return SbisWebhookResponse(
        status="accepted",
        event_id=payload.event_id,
        message="Event queued for processing",
    )


@router.get("/sbis/events", response_model=SbisWebhookEventListResponse)
async def list_sbwebhook_events(
    event_type: Optional[str] = None,
    processed: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
    current_user=Depends(get_current_user),
    _role=Depends(require_permission("sbis.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список событий СБИС.

    Требуется право: **sbis.read**
    """
    from sqlalchemy import func

    query = select(SbisWebhookEvent)

    if event_type:
        query = query.where(SbisWebhookEvent.event_type == event_type)

    if processed is not None:
        query = query.where(SbisWebhookEvent.processed == processed)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(SbisWebhookEvent.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()

    return SbisWebhookEventListResponse(
        items=[SbisWebhookEventSchema.model_validate(e) for e in events],
        total=total,
    )


@router.get("/sbis/events/{event_id}", response_model=SbisWebhookEventSchema)
async def get_sbwebhook_event(
    event_id: str,
    current_user=Depends(get_current_user),
    _role=Depends(require_permission("sbis.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить информацию о событии СБИС.

    Требуется право: **sbis.read**
    """
    result = await db.execute(
        select(SbisWebhookEvent).where(SbisWebhookEvent.event_id == event_id)
    )
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return SbisWebhookEventSchema.model_validate(event)