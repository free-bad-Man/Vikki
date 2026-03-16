"""
Celery tasks для обработки событий СБИС.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from celery_app import celery_app
from sqlalchemy import select

from app.database import sync_session_maker
from app.models.notification import Notification
from app.models.sbis_webhook_event import SbisWebhookEvent


@celery_app.task(bind=True, name="app.tasks.sbis.process_sbwebhook_event", max_retries=3)
def process_sbwebhook_event(self, event_id: str):
    """
    Обработка события вебхука СБИС.

    Args:
        event_id: ID записи события в БД (UUID)
    """
    def _coerce_uuid(value: str):
        try:
            return UUID(value)
        except Exception:
            return value  # fallback: пусть драйвер/ORM попробует сам

    db_event_id = _coerce_uuid(event_id)

    try:
        with sync_session_maker() as db:
            result = db.execute(
                select(SbisWebhookEvent).where(SbisWebhookEvent.id == db_event_id)
            )
            event = result.scalar_one_or_none()

            if event is None:
                return {"status": "error", "message": "Event not found"}

            if event.processed:
                return {"status": "skipped", "message": "Event already processed"}

            # КРИТИЧНО: без tenant_id нельзя создавать нотификации/обрабатывать
            if event.tenant_id is None:
                event.processing_error = "Missing tenant_id on SbisWebhookEvent; skipping to avoid infinite retries"
                event.processed = True
                db.commit()
                return {"status": "skipped", "message": "Missing tenant_id; event marked processed", "event_id": event.event_id}

            # Обрабатываем в зависимости от типа события
            if event.event_type == "document.created":
                _handle_document_created(db, event)
            elif event.event_type == "document.signed":
                _handle_document_signed(db, event)
            elif event.event_type == "document.rejected":
                _handle_document_rejected(db, event)
            else:
                _handle_unknown_event(db, event)

            event.processed = True
            db.commit()

            return {"status": "success", "event_id": event.event_id}

    except Exception as exc:
        # Записываем ошибку в событие (если можем)
        try:
            with sync_session_maker() as db:
                result = db.execute(
                    select(SbisWebhookEvent).where(SbisWebhookEvent.id == db_event_id)
                )
                event = result.scalar_one_or_none()
                if event:
                    event.processing_error = str(exc)
                    db.commit()
        except Exception:
            pass

        raise self.retry(exc=exc, countdown=60)


def _handle_document_created(db, event: SbisWebhookEvent):
    """Обработка события создания документа."""
    notification = Notification(
        tenant_id=event.tenant_id,
        user_id=_get_tenant_owner_id(db, event.tenant_id),
        title="Новый документ из СБИС",
        message=f"Документ {event.payload.get('document_id', 'unknown')} создан",
        notification_type="info",
        payload=event.payload,
        related_type="sbis_document",
        related_id=event.payload.get("document_id"),
    )
    db.add(notification)


def _handle_document_signed(db, event: SbisWebhookEvent):
    """Обработка события подписания документа."""
    notification = Notification(
        tenant_id=event.tenant_id,
        user_id=_get_tenant_owner_id(db, event.tenant_id),
        title="Документ подписан в СБИС",
        message=f"Документ {event.payload.get('document_id', 'unknown')} подписан",
        notification_type="success",
        payload=event.payload,
        related_type="sbis_document",
        related_id=event.payload.get("document_id"),
    )
    db.add(notification)


def _handle_document_rejected(db, event: SbisWebhookEvent):
    """Обработка события отклонения документа."""
    notification = Notification(
        tenant_id=event.tenant_id,
        user_id=_get_tenant_owner_id(db, event.tenant_id),
        title="Документ отклонён в СБИС",
        message=f"Документ {event.payload.get('document_id', 'unknown')} отклонён",
        notification_type="warning",
        payload=event.payload,
        related_type="sbis_document",
        related_id=event.payload.get("document_id"),
    )
    db.add(notification)


def _handle_unknown_event(db, event: SbisWebhookEvent):
    """Обработка неизвестного типа события."""
    notification = Notification(
        tenant_id=event.tenant_id,
        user_id=_get_tenant_owner_id(db, event.tenant_id),
        title=f"Событие СБИС: {event.event_type}",
        message="Получено новое событие от СБИС",
        notification_type="info",
        payload=event.payload,
    )
    db.add(notification)


def _get_tenant_owner_id(db, tenant_id: str) -> str | None:
    """
    Получить ID владельца tenant.
    """
    from app.models.membership import Membership

    result = db.execute(
        select(Membership).where(
            Membership.tenant_id == tenant_id,
            Membership.is_owner == True,
            Membership.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        return membership.user_id

    # Если владельца нет, возвращаем первого пользователя
    from app.models.user import User

    result = db.execute(
        select(User)
        .where(
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )
        .limit(1)
    )
    user = result.scalar_one_or_none()
    return user.id if user else None