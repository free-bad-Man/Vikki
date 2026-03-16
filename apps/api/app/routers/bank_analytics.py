from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Optional, Literal

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_permission
from app.models.transaction import Transaction
from app.schemas.bank_analytics import (
    SummaryResponse,
    TopListResponse,
    CashflowResponse,
    CashflowPoint,
    TopItem,
)

GroupBy = Literal["day", "week", "month"]
TxnType = Literal["incoming", "outgoing"]

router = APIRouter(prefix="/bank/analytics", tags=["Bank Analytics"])


def _date_bounds(date_from: Optional[date], date_to: Optional[date]) -> tuple[date, date]:
    today = date.today()
    if date_to is None:
        date_to = today
    if date_from is None:
        date_from = date_to - timedelta(days=30)
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be <= date_to")
    return date_from, date_to


def _dt_from(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)


def _dt_to_exclusive(d: date) -> datetime:
    return _dt_from(d) + timedelta(days=1)


def _base_filters(
    tenant_id: str,
    date_from: date,
    date_to: date,
    bank_account_id: Optional[str],
):
    filters = [
        Transaction.tenant_id == tenant_id,
        Transaction.deleted_at.is_(None),
        Transaction.occurred_at >= _dt_from(date_from),
        Transaction.occurred_at < _dt_to_exclusive(date_to),
    ]
    if bank_account_id:
        filters.append(Transaction.bank_account_id == bank_account_id)
    return and_(*filters)


def _fix_mojibake(s: str) -> str:
    # Same heuristic as in importer task.
    if not s:
        return s
    if ("Ð" not in s) and ("Ñ" not in s):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except Exception:
        return s


def _norm_out_key(v: Optional[str]) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    return _fix_mojibake(s)


@router.get("/summary", response_model=SummaryResponse)
async def summary(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    bank_account_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("bank.write")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    date_from, date_to = _date_bounds(date_from, date_to)

    base = _base_filters(tenant_id, date_from, date_to, bank_account_id)

    income_sum = func.coalesce(
        func.sum(case((Transaction.transaction_type == "incoming", Transaction.amount), else_=0)),
        0,
    )
    expense_sum = func.coalesce(
        func.sum(case((Transaction.transaction_type == "outgoing", Transaction.amount), else_=0)),
        0,
    )

    total_count = func.count(Transaction.id)
    incoming_count = func.coalesce(func.sum(case((Transaction.transaction_type == "incoming", 1), else_=0)), 0)
    outgoing_count = func.coalesce(func.sum(case((Transaction.transaction_type == "outgoing", 1), else_=0)), 0)

    q = select(income_sum, expense_sum, total_count, incoming_count, outgoing_count).where(base)
    r = await db.execute(q)
    income, expense, ops, inc_cnt, out_cnt = r.one()

    income_f = float(income or 0)
    expense_f = float(expense or 0)
    ops_i = int(ops or 0)
    inc_i = int(inc_cnt or 0)
    out_i = int(out_cnt or 0)

    avg_income = float(income_f / inc_i) if inc_i > 0 else 0.0
    avg_expense = float(expense_f / out_i) if out_i > 0 else 0.0

    return SummaryResponse(
        date_from=date_from,
        date_to=date_to,
        bank_account_id=bank_account_id,
        total_income=income_f,
        total_expense=expense_f,
        net_cashflow=income_f - expense_f,
        operations_count=ops_i,
        incoming_count=inc_i,
        outgoing_count=out_i,
        avg_income_check=avg_income,
        avg_expense_check=avg_expense,
    )


@router.get("/top-counterparties", response_model=TopListResponse)
async def top_counterparties(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    bank_account_id: Optional[str] = Query(None),
    transaction_type: Optional[TxnType] = Query(None, description="incoming|outgoing"),
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("bank.write")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    date_from, date_to = _date_bounds(date_from, date_to)

    base = _base_filters(tenant_id, date_from, date_to, bank_account_id)
    filters = [base]

    if transaction_type:
        filters.append(Transaction.transaction_type == transaction_type)

    key_expr = func.coalesce(func.nullif(Transaction.counterparty_name, ""), func.nullif(Transaction.counterparty_inn, ""))
    q = (
        select(
            key_expr.label("k"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .where(and_(*filters))
        .where(key_expr.isnot(None))
        .group_by(key_expr)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
    )

    res = await db.execute(q)
    rows = res.all()

    return TopListResponse(
        date_from=date_from,
        date_to=date_to,
        bank_account_id=bank_account_id,
        transaction_type=transaction_type,
        limit=limit,
        items=[
            TopItem(
                key=_norm_out_key(k),
                total=float(t or 0),
                operations_count=int(c or 0),
            )
            for (k, t, c) in rows
        ],
    )


@router.get("/top-purposes", response_model=TopListResponse)
async def top_purposes(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    bank_account_id: Optional[str] = Query(None),
    transaction_type: Optional[TxnType] = Query(None, description="incoming|outgoing"),
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("bank.write")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    date_from, date_to = _date_bounds(date_from, date_to)

    base = _base_filters(tenant_id, date_from, date_to, bank_account_id)
    filters = [base]

    if transaction_type:
        filters.append(Transaction.transaction_type == transaction_type)

    key_expr = func.nullif(func.trim(Transaction.description), "")
    q = (
        select(
            key_expr.label("k"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .where(and_(*filters))
        .where(key_expr.isnot(None))
        .group_by(key_expr)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
    )

    res = await db.execute(q)
    rows = res.all()

    return TopListResponse(
        date_from=date_from,
        date_to=date_to,
        bank_account_id=bank_account_id,
        transaction_type=transaction_type,
        limit=limit,
        items=[
            TopItem(
                key=_norm_out_key(k),
                total=float(t or 0),
                operations_count=int(c or 0),
            )
            for (k, t, c) in rows
        ],
    )


@router.get("/cashflow", response_model=CashflowResponse)
async def cashflow(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    bank_account_id: Optional[str] = Query(None),
    group_by: GroupBy = Query("day", description="day|week|month"),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("bank.write")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    date_from, date_to = _date_bounds(date_from, date_to)

    base = _base_filters(tenant_id, date_from, date_to, bank_account_id)

    period = func.date_trunc(group_by, Transaction.occurred_at).label("period_start")

    income_sum = func.coalesce(
        func.sum(case((Transaction.transaction_type == "incoming", Transaction.amount), else_=0)),
        0,
    ).label("income")

    expense_sum = func.coalesce(
        func.sum(case((Transaction.transaction_type == "outgoing", Transaction.amount), else_=0)),
        0,
    ).label("expense")

    q = (
        select(period, income_sum, expense_sum)
        .where(base)
        .group_by(period)
        .order_by(period.asc())
    )

    res = await db.execute(q)
    rows = res.all()

    points = []
    for p, inc, exp in rows:
        inc_f = float(inc or 0)
        exp_f = float(exp or 0)
        points.append(CashflowPoint(period_start=p, income=inc_f, expense=exp_f, net=inc_f - exp_f))

    return CashflowResponse(
        date_from=date_from,
        date_to=date_to,
        bank_account_id=bank_account_id,
        group_by=group_by,
        points=points,
    )