"""
Модели данных Vikki Platform.

Core SaaS модели для мульти-тенантной архитектуры.
"""
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import Role
from app.models.membership import Membership

# Доменные модели
from app.models.bank_account import BankAccount
from app.models.transaction import Transaction
from app.models.edo_document import EdoDocument
from app.models.cash_operation import CashOperation
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.models.import_job import ImportJob

# Интеграции
from app.models.sbis_webhook_event import SbisWebhookEvent
from app.models.email_ingest_event import EmailIngestEvent

__all__ = [
    # Core
    "Tenant",
    "User",
    "Role",
    "Membership",
    # Domain
    "BankAccount",
    "Transaction",
    "EdoDocument",
    "CashOperation",
    "Notification",
    "AuditLog",
    "ImportJob",
    # Integrations
    "SbisWebhookEvent",
    "EmailIngestEvent",
]