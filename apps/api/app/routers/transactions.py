"""
CRUD router для транзакций.
"""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, case
from sqlalchemy.sql import column

from app.database import get_db
from app.models.transaction import Transaction
from app.models.bank_account import BankAccount
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
    TransactionAnalytics,
    TransactionByPeriod,
)
from app.dependencies.auth import (
    get_current_user,
    get_tenant_context,
    require_permission,
)


router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    bank_account_id: Optional[str] = Query(None, description="Фильтр по счёту"),
    transaction_type: Optional[str] = Query(None, description="Тип: incoming/outgoing"),
    date_from: Optional[date] = Query(None, description="Дата от"),
    date_to: Optional[date] = Query(None, description="Дата до"),
    limit: int = Query(20, ge=1, le=100, description="Лимит записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("transactions.read")),
):
    """
    Получить список транзакций.
    
    Требуется право: **transactions.read**
    """
    # Базовый запрос
    query = select(Transaction).where(
        Transaction.tenant_id == tenant.id,
        Transaction.deleted_at.is_(None),
    )
    
    # Фильтры
    if bank_account_id:
        query = query.where(Transaction.bank_account_id == bank_account_id)
    
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type)
    
    if date_from:
        query = query.where(Transaction.occurred_at >= datetime.combine(date_from, datetime.min.time()))
    
    if date_to:
        query = query.where(Transaction.occurred_at <= datetime.combine(date_to, datetime.max.time()))
    
    # Считаем общее количество
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Применяем лимиты
    query = query.order_by(Transaction.occurred_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(tx) for tx in transactions],
        total=total,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("transactions.read")),
):
    """
    Получить информацию о транзакции.
    
    Требуется право: **transactions.read**
    """
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.tenant_id == tenant.id,
            Transaction.deleted_at.is_(None),
        )
    )
    transaction = result.scalar_one_or_none()
    
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    
    return TransactionResponse.model_validate(transaction)


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("transactions.write")),
):
    """
    Создать новую транзакцию.
    
    Требуется право: **transactions.write**
    """
    # Проверяем существование счёта
    account_result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == transaction_data.bank_account_id,
            BankAccount.tenant_id == tenant.id,
            BankAccount.deleted_at.is_(None),
        )
    )
    account = account_result.scalar_one_or_none()
    
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found",
        )
    
    # Проверяем уникальность fingerprint если есть external_id
    if transaction_data.external_id:
        fingerprint = f"{tenant.id}:{transaction_data.external_id}"
        existing = await db.execute(
            select(Transaction).where(
                Transaction.tenant_id == tenant.id,
                Transaction.fingerprint == fingerprint,
                Transaction.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction with this external_id already exists",
            )
    
    transaction = Transaction(
        tenant_id=tenant.id,
        **transaction_data.model_dump(),
    )
    
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    
    return TransactionResponse.model_validate(transaction)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    transaction_data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("transactions.write")),
):
    """
    Обновить транзакцию.
    
    Требуется право: **transactions.write**
    """
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.tenant_id == tenant.id,
            Transaction.deleted_at.is_(None),
        )
    )
    transaction = result.scalar_one_or_none()
    
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    
    # Обновляем поля
    update_data = transaction_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)
    
    await db.commit()
    await db.refresh(transaction)
    
    return TransactionResponse.model_validate(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("transactions.delete")),
):
    """
    Удалить транзакцию (soft delete).
    
    Требуется право: **transactions.delete**
    """
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.tenant_id == tenant.id,
            Transaction.deleted_at.is_(None),
        )
    )
    transaction = result.scalar_one_or_none()
    
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    
    # Soft delete
    transaction.deleted_at = func.now()
    await db.commit()
    
    return None


# =============================================================================
# Analytics endpoints
# =============================================================================

@router.get("/analytics/summary", response_model=TransactionAnalytics)
async def get_transactions_analytics(
    date_from: Optional[date] = Query(None, description="Дата от"),
    date_to: Optional[date] = Query(None, description="Дата до"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("transactions.read")),
):
    """
    Получить сводную аналитику по транзакциям.
    
    Требуется право: **transactions.read**
    """
    # Базовые условия
    base_conditions = [
        Transaction.tenant_id == tenant.id,
        Transaction.deleted_at.is_(None),
    ]
    
    if date_from:
        base_conditions.append(Transaction.occurred_at >= datetime.combine(date_from, datetime.min.time()))
    
    if date_to:
        base_conditions.append(Transaction.occurred_at <= datetime.combine(date_to, datetime.max.time()))
    
    # Запрос для агрегации
    result = await db.execute(
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
            func.count(
                case(
                    (Transaction.transaction_type == "incoming", 1),
                    else_=None,
                )
            ).label("income_count"),
            func.count(
                case(
                    (Transaction.transaction_type == "outgoing", 1),
                    else_=None,
                )
            ).label("outcome_count"),
        ).where(and_(*base_conditions))
    )
    
    row = result.first()
    
    total_income = float(row[0] or 0)
    total_outcome = float(row[1] or 0)
    income_count = row[2] or 0
    outcome_count = row[3] or 0
    
    return TransactionAnalytics(
        total_income=total_income,
        total_outcome=total_outcome,
        income_count=income_count,
        outcome_count=outcome_count,
        balance=total_income - total_outcome,
    )


@router.get("/analytics/by-period", response_model=list[TransactionByPeriod])
async def get_transactions_by_period(
    months: int = Query(6, ge=1, le=24, description="Количество месяцев"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("transactions.read")),
):
    """
    Получить транзакции по периодам (месяцам).
    
    Требуется право: **transactions.read**
    """
    # Запрос для группировки по месяцам
    period_label = func.to_char(Transaction.occurred_at, "YYYY-MM").label("period")
    
    result = await db.execute(
        select(
            period_label,
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
            func.count().label("count"),
        ).where(
            Transaction.tenant_id == tenant.id,
            Transaction.deleted_at.is_(None),
        )
        .group_by(period_label)
        .order_by(period_label.desc())
        .limit(months)
    )
    
    rows = result.all()
    
    return [
        TransactionByPeriod(
            period=row[0],
            income=float(row[1] or 0),
            outcome=float(row[2] or 0),
            count=row[3] or 0,
        )
        for row in rows
    ]
