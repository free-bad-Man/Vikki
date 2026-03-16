"""
Схемы Vikki Platform.
"""
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserSchema,
    TokenData,
)
from app.schemas.bank_account import (
    BankAccountBase,
    BankAccountCreate,
    BankAccountUpdate,
    BankAccountResponse,
    BankAccountListResponse,
)
from app.schemas.transaction import (
    TransactionBase,
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
    TransactionAnalytics,
    TransactionByPeriod,
)
from app.schemas.edo_document import (
    EdoDocumentBase,
    EdoDocumentCreate,
    EdoDocumentUpdate,
    EdoDocumentResponse,
    EdoDocumentListResponse,
)
from app.schemas.cash_operation import (
    CashOperationBase,
    CashOperationCreate,
    CashOperationUpdate,
    CashOperationResponse,
    CashOperationListResponse,
)
from app.schemas.sbis_webhook import (
    SbisWebhookPayload,
    SbisWebhookResponse,
    SbisWebhookEventSchema,
    SbisWebhookEventListResponse,
)
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationUpdate,
)
from app.schemas.analytics import (
    FinancialSummary,
    CashFlowItem,
    CounterpartyAnalytics,
    AnalyticsByCategory,
    DashboardResponse,
)

__all__ = [
    # Auth
    "LoginRequest",
    "TokenResponse",
    "UserSchema",
    "TokenData",
    # Bank Account
    "BankAccountBase",
    "BankAccountCreate",
    "BankAccountUpdate",
    "BankAccountResponse",
    "BankAccountListResponse",
    # Transaction
    "TransactionBase",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "TransactionListResponse",
    "TransactionAnalytics",
    "TransactionByPeriod",
    # Edo Document
    "EdoDocumentBase",
    "EdoDocumentCreate",
    "EdoDocumentUpdate",
    "EdoDocumentResponse",
    "EdoDocumentListResponse",
    # Cash Operation
    "CashOperationBase",
    "CashOperationCreate",
    "CashOperationUpdate",
    "CashOperationResponse",
    "CashOperationListResponse",
    # Sbis Webhook
    "SbisWebhookPayload",
    "SbisWebhookResponse",
    "SbisWebhookEventSchema",
    "SbisWebhookEventListResponse",
    # Notification
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationUpdate",
    # Analytics
    "FinancialSummary",
    "CashFlowItem",
    "CounterpartyAnalytics",
    "AnalyticsByCategory",
    "DashboardResponse",
]
