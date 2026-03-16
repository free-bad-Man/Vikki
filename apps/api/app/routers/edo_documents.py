"""
CRUD router для документов ЭДО.
"""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.edo_document import EdoDocument
from app.models.bank_account import BankAccount
from app.models.transaction import Transaction
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.edo_document import (
    EdoDocumentCreate,
    EdoDocumentUpdate,
    EdoDocumentResponse,
    EdoDocumentListResponse,
)
from app.dependencies.auth import (
    get_current_user,
    get_tenant_context,
    require_permission,
)


router = APIRouter(prefix="/edo-documents", tags=["Edo Documents"])


@router.get("", response_model=EdoDocumentListResponse)
async def list_edo_documents(
    document_type: Optional[str] = Query(None, description="Тип документа"),
    status: Optional[str] = Query(None, description="Статус"),
    date_from: Optional[date] = Query(None, description="Дата от"),
    date_to: Optional[date] = Query(None, description="Дата до"),
    limit: int = Query(20, ge=1, le=100, description="Лимит записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("edo_documents.read")),
):
    """
    Получить список документов.
    
    Требуется право: **edo_documents.read**
    """
    # Базовый запрос
    query = select(EdoDocument).where(
        EdoDocument.tenant_id == tenant.id,
        EdoDocument.deleted_at.is_(None),
    )
    
    # Фильтры
    if document_type:
        query = query.where(EdoDocument.document_type == document_type)
    
    if status:
        query = query.where(EdoDocument.status == status)
    
    if date_from:
        query = query.where(EdoDocument.document_date >= datetime.combine(date_from, datetime.min.time()))
    
    if date_to:
        query = query.where(EdoDocument.document_date <= datetime.combine(date_to, datetime.max.time()))
    
    # Считаем общее количество
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Применяем лимиты
    query = query.order_by(EdoDocument.document_date.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return EdoDocumentListResponse(
        items=[EdoDocumentResponse.model_validate(doc) for doc in documents],
        total=total,
    )


@router.get("/{document_id}", response_model=EdoDocumentResponse)
async def get_edo_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("edo_documents.read")),
):
    """
    Получить информацию о документе.
    
    Требуется право: **edo_documents.read**
    """
    result = await db.execute(
        select(EdoDocument).where(
            EdoDocument.id == document_id,
            EdoDocument.tenant_id == tenant.id,
            EdoDocument.deleted_at.is_(None),
        )
    )
    document = result.scalar_one_or_none()
    
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return EdoDocumentResponse.model_validate(document)


@router.post("", response_model=EdoDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_edo_document(
    document_data: EdoDocumentCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("edo_documents.write")),
):
    """
    Создать новый документ.
    
    Требуется право: **edo_documents.write**
    """
    # Проверяем существование счёта если указан
    if document_data.bank_account_id:
        account_result = await db.execute(
            select(BankAccount).where(
                BankAccount.id == document_data.bank_account_id,
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
    
    # Проверяем существование транзакции если указана
    if document_data.transaction_id:
        tx_result = await db.execute(
            select(Transaction).where(
                Transaction.id == document_data.transaction_id,
                Transaction.tenant_id == tenant.id,
                Transaction.deleted_at.is_(None),
            )
        )
        transaction = tx_result.scalar_one_or_none()
        
        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found",
            )
    
    # Проверяем уникальность номера в рамках tenant
    existing = await db.execute(
        select(EdoDocument).where(
            EdoDocument.tenant_id == tenant.id,
            EdoDocument.document_number == document_data.document_number,
            EdoDocument.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document with this number already exists",
        )
    
    document = EdoDocument(
        tenant_id=tenant.id,
        **document_data.model_dump(),
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    return EdoDocumentResponse.model_validate(document)


@router.patch("/{document_id}", response_model=EdoDocumentResponse)
async def update_edo_document(
    document_id: str,
    document_data: EdoDocumentUpdate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("edo_documents.write")),
):
    """
    Обновить документ.
    
    Требуется право: **edo_documents.write**
    """
    result = await db.execute(
        select(EdoDocument).where(
            EdoDocument.id == document_id,
            EdoDocument.tenant_id == tenant.id,
            EdoDocument.deleted_at.is_(None),
        )
    )
    document = result.scalar_one_or_none()
    
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Обновляем поля
    update_data = document_data.model_dump(exclude_unset=True, by_alias=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    await db.commit()
    await db.refresh(document)
    
    return EdoDocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edo_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    _role = Depends(require_permission("edo_documents.delete")),
):
    """
    Удалить документ (soft delete).
    
    Требуется право: **edo_documents.delete**
    """
    result = await db.execute(
        select(EdoDocument).where(
            EdoDocument.id == document_id,
            EdoDocument.tenant_id == tenant.id,
            EdoDocument.deleted_at.is_(None),
        )
    )
    document = result.scalar_one_or_none()
    
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Soft delete
    document.deleted_at = func.now()
    await db.commit()
    
    return None
