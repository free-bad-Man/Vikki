from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, Literal, List

from pydantic import BaseModel, Field


ImportJobStatus = Literal["PENDING", "PROCESSING", "SUCCESS", "FAILED"]


class ImportJobResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: Optional[str] = None

    source: str
    file_name: str
    file_mime: Optional[str] = None
    file_size: Optional[int] = None

    s3_bucket: str
    s3_key: str
    file_sha256: str

    status: ImportJobStatus

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    total_rows: int = 0
    inserted_rows: int = 0
    skipped_rows: int = 0
    failed_rows: int = 0

    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ImportJobListResponse(BaseModel):
    items: List[ImportJobResponse]
    total: int