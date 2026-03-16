"""
Модель ImportJob — задания на импорт (банковские выписки и т.п.).

Жизненный цикл: PENDING -> PROCESSING -> SUCCESS | FAILED
Идемпотентность: (tenant_id, file_sha256) + (tenant_id, file_sha256, bank_account_id в meta) на уровне логики.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import (
    String,
    ForeignKey,
    Index,
    DateTime,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, SoftDeleteMixin


def _utcnow():
    return datetime.now(timezone.utc)


class ImportJob(Base, SoftDeleteMixin):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=lambda: str(uuid.uuid4()))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="bank")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_mime: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    s3_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)

    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    tenant = relationship("Tenant", lazy="joined")
    user = relationship("User", lazy="joined")
    transactions = relationship(
        "Transaction",
        back_populates="import_job",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_import_jobs_tenant_status_created", "tenant_id", "status", "created_at"),
        Index("ux_import_jobs_tenant_file_sha256", "tenant_id", "file_sha256", unique=True),
        Index("ix_import_jobs_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<ImportJob(id={self.id}, source='{self.source}', status='{self.status}')>"