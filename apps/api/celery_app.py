from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "vikki",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

APP_TZ = os.getenv("DAILY_DIGEST_TIMEZONE", "Europe/Moscow")

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=APP_TZ,
    enable_utc=True,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    imports=[
        "app.tasks.sbis",
        "app.tasks.bank_import",
        "app.tasks.imap_ingest",
        "app.tasks.daily_digest",
    ],
)

beat_schedule: dict = {
    "imap-poll-job": {
        "task": "app.tasks.imap_ingest.imap_poll_job",
        "schedule": settings.IMAP_POLL_INTERVAL_MINUTES * 60,
    }
}

if os.getenv("DAILY_DIGEST_ENABLED", "false").lower() == "true":
    hour = int(os.getenv("DAILY_DIGEST_TIME_HOUR", "9"))
    minute = int(os.getenv("DAILY_DIGEST_TIME_MINUTE", "0"))
    beat_schedule["daily-digest-job"] = {
        "task": "app.tasks.daily_digest.daily_digest_job",
        "schedule": crontab(hour=hour, minute=minute),
    }

celery_app.conf.beat_schedule = beat_schedule