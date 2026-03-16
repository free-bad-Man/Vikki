from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


GroupBy = Literal["day", "week", "month"]
TxnType = Literal["incoming", "outgoing"]


class AnalyticsPeriod(BaseModel):
    date_from: date
    date_to: date
    bank_account_id: Optional[str] = None


class SummaryResponse(BaseModel):
    date_from: date
    date_to: date
    bank_account_id: Optional[str] = None

    total_income: float = 0.0
    total_expense: float = 0.0
    net_cashflow: float = 0.0

    operations_count: int = 0
    incoming_count: int = 0
    outgoing_count: int = 0

    avg_income_check: float = 0.0
    avg_expense_check: float = 0.0


class TopItem(BaseModel):
    key: str
    total: float
    operations_count: int = 0


class TopListResponse(BaseModel):
    date_from: date
    date_to: date
    bank_account_id: Optional[str] = None
    transaction_type: Optional[TxnType] = None
    limit: int = 10
    items: List[TopItem] = Field(default_factory=list)


class CashflowPoint(BaseModel):
    period_start: datetime
    income: float = 0.0
    expense: float = 0.0
    net: float = 0.0


class CashflowResponse(BaseModel):
    date_from: date
    date_to: date
    bank_account_id: Optional[str] = None
    group_by: GroupBy
    points: List[CashflowPoint] = Field(default_factory=list)