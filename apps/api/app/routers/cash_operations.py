"""
CRUD router для кассовых операций.
"""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.cash_operation import CashOperation
from app.models.bank_account import BankAccount
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.cash_operation import (
    CashOperationCreate,
    CashOperationUpdate,
    CashOperationResponse,
    CashOperationListResponse,
)
from app.dependencies.auth import (
    get_current_user,
    get_tenant_context,
    require_permission,
)


router = APIRouter(prefix="/cash-operations", tags=["Cash Operations"])


@router.get("", response_model=CashOperationListResponse)
async def list_cash_operations(
    operation_type: Optional[str] = Query(None, description="Тип: income/expense"),
    date_from: Optional[date] = Query(None, description="Дата от"),
    date_to: Optional[date] = Query(None, description="Дата до"),
    limit: int = Query(20, ge=1, le=100, description="Лимит записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("cash_operations.read")),
):
    """
    Получить список кассовых операций.
    
    Требуется право: **cash_operations.read**
    """
    # Базовый запрос
    query = select(CashOperation).where(
        CashOperation.tenant_id == tenant.id,
        CashOperation.deleted_at.is_(None),
    )
    
    # Фильтры
    if operation_type:
        query = query.where(CashOperation.operation_type == operation_type)
    
    if date_from:
        query = query.where(CashOperation.document_date >= datetime.combine(date_from, datetime.min.time()))
    
    if date_to:
        query = query.where(CashOperation.document_date <= datetime.combine(date_to, datetime.max.time()))
    
    # Считаем общее количество
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Применяем лимиты
    query = query.order_by(CashOperation.document_date.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    operations = result.scalars().all()
    
    return CashOperationListResponse(
        items=[CashOperationResponse.model_validate(op) for op in operations],
        total=total,
    )


@router.get("/{operation_id}", response_model=CashOperationResponse)
async def get_cash_operation(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("cash_operations.read")),
):
    """
    Получить информацию о кассовой операции.
    
    Требуется право: **cash_operations.read**
    """
    result = await db.execute(
        select(CashOperation).where(
            CashOperation.id == operation_id,
            CashOperation.tenant_id == tenant.id,
            CashOperation.deleted_at.is_(None),
        )
    )
    operation = result.scalar_one_or_none()
    
    if operation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash operation not found",
        )
    
    return CashOperationResponse.model_validate(operation)


@router.post("", response_model=CashOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_cash_operation(
    operation_data: CashOperationCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("cash_operations.write")),
):
    """
    Создать новую кассовую операцию.
    
    Требуется право: **cash_operations.write**
    """
    # Проверяем существование счёта если указан
    if operation_data.bank_account_id:
        account_result = await db.execute(
            select(BankAccount).where(
                BankAccount.id == operation_data.bank_account_id,
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
    
    # Проверяем уникальность номера ордера в рамках tenant
    existing = await db.execute(
        select(CashOperation).where(
            CashOperation.tenant_id == tenant.id,
            CashOperation.document_number == operation_data.document_number,
            CashOperation.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cash operation with this number already exists",
        )
    
    operation = CashOperation(
        tenant_id=tenant.id,
        **operation_data.model_dump(),
    )
    
    db.add(operation)
    await db.commit()
    await db.refresh(operation)
    
    return CashOperationResponse.model_validate(operation)


@router.patch("/{operation_id}", response_model=CashOperationResponse)
async def update_cash_operation(
    operation_id: str,
    operation_data: CashOperationUpdate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("cash_operations.write")),
):
    """
    Обновить кассовую операцию.
    
    Требуется право: **cash_operations.write**
    """
    result = await db.execute(
        select(CashOperation).where(
            CashOperation.id == operation_id,
            CashOperation.tenant_id == tenant.id,
            CashOperation.deleted_at.is_(None),
        )
    )
    operation = result.scalar_one_or_none()
    
    if operation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash operation not found",
        )
    
    # Обновляем поля
    update_data = operation_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(operation, field, value)
    
    await db.commit()
    await db.refresh(operation)
    
    return CashOperationResponse.model_validate(operation)


@router.delete("/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cash_operation(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("cash_operations.delete")),
):
    """
    Удалить кассовую операцию (soft delete).
    
    Требуется право: **cash_operations.delete**
    """
    result = await db.execute(
        select(CashOperation).where(
            CashOperation.id == operation_id,
            CashOperation.tenant_id == tenant.id,
            CashOperation.deleted_at.is_(None),
        )
    )
    operation = result.scalar_one_or_none()
    
    if operation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash operation not found",
        )
    
    # Soft delete
    operation.deleted_at = func.now()
    await db.commit()
    
    return None
