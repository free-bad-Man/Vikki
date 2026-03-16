"""
Схемы для аналитики.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FinancialSummary(BaseModel):
    """Финансовая сводка."""
    total_income: float = Field(..., description="Всего доходов")
    total_outcome: float = Field(..., description="Всего расходов")
    balance: float = Field(..., description="Сальдо")
    bank_accounts_count: int = Field(..., description="Количество счетов")
    transactions_count: int = Field(..., description="Количество транзакций")


class CashFlowItem(BaseModel):
    """Элемент денежного потока."""
    date: str
    income: float
    outcome: float
    balance: float


class CounterpartyAnalytics(BaseModel):
    """Аналитика по контрагенту."""
    counterparty_name: str
    counterparty_inn: Optional[str] = None
    total_income: float = 0
    total_outcome: float = 0
    transactions_count: int = 0


class AnalyticsByCategory(BaseModel):
    """Аналитика по категории."""
    category: str
    amount: float
    count: int


class DashboardResponse(BaseModel):
    """Ответ дашборда."""
    financial_summary: FinancialSummary
    cash_flow: List[CashFlowItem]
    top_counterparties: List[CounterpartyAnalytics]
    recent_transactions: List[dict]
