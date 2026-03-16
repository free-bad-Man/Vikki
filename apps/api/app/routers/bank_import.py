from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.dependencies.auth import get_current_user, require_permission
from app.models.import_job import ImportJob
from app.models.bank_account import BankAccount
from app.schemas.import_job import ImportJobResponse, ImportJobListResponse
from app.schemas.bank_account import BankAccountResponse, BankAccountListResponse
from app.services.storage_s3 import put_bytes, sha256_bytes
from app.tasks.bank_import import import_bank_statement_job


router = APIRouter(prefix="/bank", tags=["Bank Import"])


@router.get("/accounts", response_model=BankAccountListResponse)
async def list_bank_accounts(
    is_active: Optional[bool] = Query(True, description="Фильтр по активности счета"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("bank.write")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id

    query = select(BankAccount).where(
        BankAccount.tenant_id == tenant_id,
        BankAccount.deleted_at.is_(None),
    )

    if is_active is not None:
        query = query.where(BankAccount.is_active.is_(is_active))

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = int(total_res.scalar() or 0)

    query = query.order_by(BankAccount.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    items = res.scalars().all()

    return BankAccountListResponse(
        items=[BankAccountResponse.model_validate(x) for x in items],
        total=total,
    )


@router.post("/upload", response_model=ImportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_bank_statement(
    bank_account_id: str = Query(..., description="ID банковского счёта (обязателен, т.к. счетов может быть несколько)"),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("bank.write")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    user_id = current_user.id

    # Проверяем, что счет принадлежит tenant и активен
    acc_res = await db.execute(
        select(BankAccount).where(
            BankAccount.id == bank_account_id,
            BankAccount.tenant_id == tenant_id,
            BankAccount.deleted_at.is_(None),
            BankAccount.is_active.is_(True),
        )
    )
    if acc_res.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Bank account not found or inactive for this tenant")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    file_hash = sha256_bytes(data)

    # Логическая идемпотентность: одинаковый файл + тот же bank_account_id => вернем существующий job
    existing = await db.execute(
        select(ImportJob).where(
            ImportJob.tenant_id == tenant_id,
            ImportJob.file_sha256 == file_hash,
            ImportJob.deleted_at.is_(None),
            (ImportJob.meta["bank_account_id"].astext == bank_account_id),
        )
    )
    job = existing.scalar_one_or_none()
    if job is not None:
        return ImportJobResponse.model_validate(job)

    s3_key = f"bank/{tenant_id}/{datetime.now(timezone.utc).strftime('%Y%m%d')}/{uuid.uuid4()}_{file.filename}"
    ref = put_bytes(s3_key, data, content_type=file.content_type)

    job = ImportJob(
        tenant_id=tenant_id,
        user_id=user_id,
        source="bank",
        file_name=file.filename or "upload.bin",
        file_mime=file.content_type,
        file_size=len(data),
        s3_bucket=ref.bucket,
        s3_key=ref.key,
        file_sha256=file_hash,
        status="PENDING",
        meta={
            "bank_account_id": bank_account_id,
            "upload": {"original_name": file.filename, "content_type": file.content_type},
        },
    )

    db.add(job)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        res = await db.execute(
            select(ImportJob).where(
                ImportJob.tenant_id == tenant_id,
                ImportJob.file_sha256 == file_hash,
                ImportJob.deleted_at.is_(None),
            )
        )
        job2 = res.scalar_one_or_none()
        if job2 is None:
            raise
        return ImportJobResponse.model_validate(job2)

    await db.refresh(job)
    import_bank_statement_job.delay(str(job.id))
    return ImportJobResponse.model_validate(job)


@router.get("/import-jobs", response_model=ImportJobListResponse)
async def list_import_jobs(
    status_filter: Optional[str] = Query(None, alias="status", description="PENDING|PROCESSING|SUCCESS|FAILED"),
    bank_account_id: Optional[str] = Query(None, description="Фильтр по bank_account_id (meta.bank_account_id)"),
    date_from: Optional[date] = Query(None, description="Дата начала (created_at)"),
    date_to: Optional[date] = Query(None, description="Дата окончания (created_at)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("bank.write")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id

    query = select(ImportJob).where(
        ImportJob.tenant_id == tenant_id,
        ImportJob.deleted_at.is_(None),
    )

    if status_filter:
        query = query.where(ImportJob.status == status_filter)

    if bank_account_id:
        query = query.where(ImportJob.meta["bank_account_id"].astext == bank_account_id)

    if date_from:
        query = query.where(ImportJob.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))

    if date_to:
        query = query.where(ImportJob.created_at < datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc))

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = int(total_res.scalar() or 0)

    query = query.order_by(ImportJob.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    items = res.scalars().all()

    return ImportJobListResponse(
        items=[ImportJobResponse.model_validate(x) for x in items],
        total=total,
    )


@router.get("/import-jobs/{job_id}", response_model=ImportJobResponse)
async def get_import_job(
    job_id: str,
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("bank.write")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id

    res = await db.execute(
        select(ImportJob).where(
            ImportJob.id == job_id,
            ImportJob.tenant_id == tenant_id,
            ImportJob.deleted_at.is_(None),
        )
    )
    job = res.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found")

    return ImportJobResponse.model_validate(job)


@router.post("/import-jobs/{job_id}/retry", response_model=ImportJobResponse)
async def retry_import_job(
    job_id: str,
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("bank.write")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id

    res = await db.execute(
        select(ImportJob).where(
            ImportJob.id == job_id,
            ImportJob.tenant_id == tenant_id,
            ImportJob.deleted_at.is_(None),
        )
    )
    job = res.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found")

    if job.status in ("PENDING", "PROCESSING"):
        return ImportJobResponse.model_validate(job)

    job.status = "PENDING"
    job.error = None
    job.started_at = None
    job.finished_at = None
    job.total_rows = 0
    job.inserted_rows = 0
    job.skipped_rows = 0
    job.failed_rows = 0

    await db.commit()
    await db.refresh(job)

    import_bank_statement_job.delay(str(job.id))
    return ImportJobResponse.model_validate(job)