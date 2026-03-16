"""
Celery tasks Vikki Platform.
"""
# Явно импортируем задачи для регистрации
from app.tasks import sbis  # noqa: F401

__all__ = [
    "sbis",
]

