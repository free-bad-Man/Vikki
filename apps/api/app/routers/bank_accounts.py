"""
CRUD router для банковских счетов.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.bank_account import BankAccount
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.bank_account import (
    BankAccountCreate,
    BankAccountUpdate,
    BankAccountResponse,
    BankAccountListResponse,
)
from app.dependencies.auth import (
    get_current_user,
    get_tenant_context,
    require_permission,
)


router = APIRouter(prefix="/bank-accounts", tags=["Bank Accounts"])


@router.get("", response_model=BankAccountListResponse)
async def list_bank_accounts(
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    limit: int = Query(20, ge=1, le=100, description="Лимит записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("bank_accounts.read")),
):
    """
    Получить список счетов tenant.
    
    Требуется право: **bank_accounts.read**
    """
    # Базовый запрос
    query = select(BankAccount).where(
        BankAccount.tenant_id == tenant.id,
        BankAccount.deleted_at.is_(None),
    )
    
    # Фильтр по активности
    if is_active is not None:
        query = query.where(BankAccount.is_active == is_active)
    
    # Считаем общее количество
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Применяем лимиты
    query = query.order_by(BankAccount.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    return BankAccountListResponse(
        items=[BankAccountResponse.model_validate(acc) for acc in accounts],
        total=total,
    )


@router.get("/{account_id}", response_model=BankAccountResponse)
async def get_bank_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("bank_accounts.read")),
):
    """
    Получить информацию о счёте.
    
    Требуется право: **bank_accounts.read**
    """
    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.tenant_id == tenant.id,
            BankAccount.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found",
        )
    
    return BankAccountResponse.model_validate(account)


@router.post("", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    account_data: BankAccountCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("bank_accounts.write")),
):
    """
    Создать новый счёт.
    
    Требуется право: **bank_accounts.write**
    """
    # Проверяем уникальность номера счёта в рамках tenant
    existing = await db.execute(
        select(BankAccount).where(
            BankAccount.tenant_id == tenant.id,
            BankAccount.account_number == account_data.account_number,
            BankAccount.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account with this number already exists",
        )
    
    account = BankAccount(
        tenant_id=tenant.id,
        **account_data.model_dump(),
    )
    
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    return BankAccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=BankAccountResponse)
async def update_bank_account(
    account_id: str,
    account_data: BankAccountUpdate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("bank_accounts.write")),
):
    """
    Обновить счёт.
    
    Требуется право: **bank_accounts.write**
    """
    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.tenant_id == tenant.id,
            BankAccount.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found",
        )
    
    # Обновляем поля
    update_data = account_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
    
    await db.commit()
    await db.refresh(account)
    
    return BankAccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("bank_accounts.delete")),
):
    """
    Удалить счёт (soft delete).
    
    Требуется право: **bank_accounts.delete**
    """
    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.tenant_id == tenant.id,
            BankAccount.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found",
        )
    
    # Soft delete
    account.deleted_at = func.now()
    await db.commit()
    
    return None
