from __future__ import annotations

import uuid
from sqlalchemy import Column, String, DateTime, Text, Boolean, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.database import Base


class EmailIngestEvent(Base):
    __tablename__ = "email_ingest_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    mailbox = Column(String(255), nullable=False)
    message_uid = Column(String(255), nullable=False)

    attachment_sha256 = Column(String(64), nullable=False)
    attachment_name = Column(String(512), nullable=True)
    attachment_mime = Column(String(255), nullable=True)
    attachment_size = Column(String(32), nullable=True)

    status = Column(String(32), nullable=False, default="PENDING")  # PENDING|SUCCESS|FAILED|SKIPPED
    error = Column(Text, nullable=True)

    meta = Column(JSONB, nullable=False, default=dict)

    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "mailbox",
            "message_uid",
            "attachment_sha256",
            name="ux_email_ingest_tenant_mailbox_uid_sha",
        ),
        Index(
            "ix_email_ingest_tenant_status_created",
            "tenant_id",
            "status",
            "created_at",
        ),
    )