"""
Analytics router с SQL агрегатами.
"""
from datetime import datetime as dt, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case, extract
from sqlalchemy.sql import column

from app.database import get_db
from app.models.transaction import Transaction
from app.models.bank_account import BankAccount
from app.models.tenant import Tenant
from app.models.user import User
from app.models.cash_operation import CashOperation
from app.schemas.analytics import (
    FinancialSummary,
    CashFlowItem,
    CounterpartyAnalytics,
    DashboardResponse,
)
from app.dependencies.auth import get_current_user, get_tenant_context, require_permission


router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/financial-summary", response_model=FinancialSummary)
async def get_financial_summary(
    date_from_param: Optional[date] = Query(default=None, alias="date_from"),
    date_to_param: Optional[date] = Query(default=None, alias="date_to"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("analytics.read")),
):
    """
    Получить финансовую сводку.
    
    Требуется право: **analytics.read**
    """
    # Базовые условия для транзакций
    tx_conditions = [
        Transaction.tenant_id == tenant.id,
        Transaction.deleted_at.is_(None),
    ]
    
    if date_from_param:
        tx_conditions.append(Transaction.occurred_at >= dt.combine(date_from_param, dt.min.time()))
    if date_to_param:
        tx_conditions.append(Transaction.occurred_at <= dt.combine(date_to_param, dt.max.time()))
    
    # Запрос для агрегации транзакций
    tx_result = await db.execute(
        select(
            func.sum(
                case(
                    (Transaction.transaction_type == "incoming", Transaction.amount),
                    else_=0,
                )
            ).label("total_income"),
            func.sum(
                case(
                    (Transaction.transaction_type == "outgoing", Transaction.amount),
                    else_=0,
                )
            ).label("total_outcome"),
            func.count().label("transactions_count"),
        ).where(and_(*tx_conditions))
    )
    tx_row = tx_result.first()
    
    # Количество счетов
    accounts_result = await db.execute(
        select(func.count()).where(
            BankAccount.tenant_id == tenant.id,
            BankAccount.deleted_at.is_(None),
        )
    )
    accounts_count = accounts_result.scalar() or 0
    
    total_income = float(tx_row[0] or 0)
    total_outcome = float(tx_row[1] or 0)
    
    return FinancialSummary(
        total_income=total_income,
        total_outcome=total_outcome,
        balance=total_income - total_outcome,
        bank_accounts_count=accounts_count,
        transactions_count=tx_row[2] or 0,
    )


@router.get("/cash-flow", response_model=list[CashFlowItem])
async def get_cash_flow(
    days: int = Query(30, ge=1, le=90, description="Количество дней"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("analytics.read")),
):
    """
    Получить денежный поток по дням.
    
    Требуется право: **analytics.read**
    """
    # Запрос для группировки по дням
    result = await db.execute(
        select(
            func.date(Transaction.occurred_at).label("date"),
            func.sum(
                case(
                    (Transaction.transaction_type == "incoming", Transaction.amount),
                    else_=0,
                )
            ).label("income"),
            func.sum(
                case(
                    (Transaction.transaction_type == "outgoing", Transaction.amount),
                    else_=0,
                )
            ).label("outcome"),
        ).where(
            Transaction.tenant_id == tenant.id,
            Transaction.deleted_at.is_(None),
            Transaction.occurred_at >= dt.utcnow() - timedelta(days=days),
        )
        .group_by(func.date(Transaction.occurred_at))
        .order_by(func.date(Transaction.occurred_at))
    )
    
    rows = result.all()
    
    return [
        CashFlowItem(
            date=row[0].isoformat(),
            income=float(row[1] or 0),
            outcome=float(row[2] or 0),
            balance=(float(row[1] or 0) - float(row[2] or 0)),
        )
        for row in rows
    ]


@router.get("/counterparties", response_model=list[CounterpartyAnalytics])
async def get_counterparty_analytics(
    limit: int = Query(10, ge=1, le=100, description="Лимит записей"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("analytics.read")),
):
    """
    Получить топ контрагентов.
    
    Требуется право: **analytics.read**
    """
    result = await db.execute(
        select(
            Transaction.counterparty_name,
            Transaction.counterparty_inn,
            func.sum(
                case(
                    (Transaction.transaction_type == "incoming", Transaction.amount),
                    else_=0,
                )
            ).label("total_income"),
            func.sum(
                case(
                    (Transaction.transaction_type == "outgoing", Transaction.amount),
                    else_=0,
                )
            ).label("total_outcome"),
            func.count().label("transactions_count"),
        ).where(
            Transaction.tenant_id == tenant.id,
            Transaction.deleted_at.is_(None),
            Transaction.counterparty_name.isnot(None),
        )
        .group_by(Transaction.counterparty_name, Transaction.counterparty_inn)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
    )
    
    rows = result.all()
    
    return [
        CounterpartyAnalytics(
            counterparty_name=row[0],
            counterparty_inn=row[1],
            total_income=float(row[2] or 0),
            total_outcome=float(row[3] or 0),
            transactions_count=row[4] or 0,
        )
        for row in rows
    ]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    days: int = Query(7, ge=1, le=30, description="Дней для cash flow"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("analytics.read")),
):
    """
    Получить полный дашборд с аналитикой.
    
    Требуется право: **analytics.read**
    """
    # Финансовая сводка - упрощённая версия
    tx_conditions = [
        Transaction.tenant_id == tenant.id,
        Transaction.deleted_at.is_(None),
    ]
    
    tx_result = await db.execute(
        select(
            func.sum(
                case(
                    (Transaction.transaction_type == "incoming", Transaction.amount),
                    else_=0,
                )
            ).label("total_income"),
            func.sum(
                case(
                    (Transaction.transaction_type == "outgoing", Transaction.amount),
                    else_=0,
                )
            ).label("total_outcome"),
            func.count().label("transactions_count"),
        ).where(and_(*tx_conditions))
    )
    tx_row = tx_result.first()
    
    accounts_result = await db.execute(
        select(func.count()).where(
            BankAccount.tenant_id == tenant.id,
            BankAccount.deleted_at.is_(None),
        )
    )
    accounts_count = accounts_result.scalar() or 0
    
    total_income = float(tx_row[0] or 0)
    total_outcome = float(tx_row[1] or 0)
    
    summary = FinancialSummary(
        total_income=total_income,
        total_outcome=total_outcome,
        balance=total_income - total_outcome,
        bank_accounts_count=accounts_count,
        transactions_count=tx_row[2] or 0,
    )
    
    # Денежный поток
    cash_flow_result = await db.execute(
        select(
            func.date(Transaction.occurred_at).label("date"),
            func.sum(
                case(
                    (Transaction.transaction_type == "incoming", Transaction.amount),
                    else_=0,
                )
            ).label("income"),
            func.sum(
                case(
                    (Transaction.transaction_type == "outgoing", Transaction.amount),
                    else_=0,
                )
            ).label("outcome"),
        ).where(
            Transaction.tenant_id == tenant.id,
            Transaction.deleted_at.is_(None),
            Transaction.occurred_at >= dt.utcnow() - timedelta(days=days),
        )
        .group_by(func.date(Transaction.occurred_at))
        .order_by(func.date(Transaction.occurred_at))
    )
    cash_flow = [
        CashFlowItem(
            date=row[0].isoformat() if row[0] else "",
            income=float(row[1] or 0),
            outcome=float(row[2] or 0),
            balance=(float(row[1] or 0) - float(row[2] or 0)),
        )
        for row in cash_flow_result.all()
    ]
    
    # Топ контрагентов
    counterparties_result = await db.execute(
        select(
            Transaction.counterparty_name,
            Transaction.counterparty_inn,
            func.sum(
                case(
                    (Transaction.transaction_type == "incoming", Transaction.amount),
                    else_=0,
                )
            ).label("total_income"),
            func.sum(
                case(
                    (Transaction.transaction_type == "outgoing", Transaction.amount),
                    else_=0,
                )
            ).label("total_outcome"),
            func.count().label("transactions_count"),
        ).where(
            Transaction.tenant_id == tenant.id,
            Transaction.deleted_at.is_(None),
            Transaction.counterparty_name.isnot(None),
        )
        .group_by(Transaction.counterparty_name, Transaction.counterparty_inn)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    )
    counterparties = [
        CounterpartyAnalytics(
            counterparty_name=row[0],
            counterparty_inn=row[1],
            total_income=float(row[2] or 0),
            total_outcome=float(row[3] or 0),
            transactions_count=row[4] or 0,
        )
        for row in counterparties_result.all()
    ]
    
    # Последние транзакции
    tx_recent_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.tenant_id == tenant.id,
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.occurred_at.desc())
        .limit(5)
    )
    recent_transactions = tx_recent_result.scalars().all()
    
    return DashboardResponse(
        financial_summary=summary,
        cash_flow=cash_flow,
        top_counterparties=counterparties,
        recent_transactions=[
            {
                "id": tx.id,
                "amount": tx.amount,
                "type": tx.transaction_type,
                "counterparty": tx.counterparty_name,
                "date": tx.occurred_at.isoformat() if tx.occurred_at else "",
            }
            for tx in recent_transactions
        ],
    )
