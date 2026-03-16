from __future__ import annotations

import email
import html
import imaplib
import os
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.message import Message
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, create_engine, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from celery_app import celery_app
from app.config import settings
from app.models.email_ingest_event import EmailIngestEvent
from app.models.import_job import ImportJob
from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.user import User
from app.services.sber_link_downloader import (
    SberDnsError,
    SberDownloadError,
    SberDownloadResult,
    SberEmptyBodyError,
    SberHttpError,
    SberLinkExpiredError,
    SberTimeoutError,
    SberTlsError,
    download_sber_report,
    extract_sber_link,
)
from app.services.storage_s3 import put_bytes, sha256_bytes
from app.tasks.bank_import import import_bank_statement_job


GENERIC_URL_RE = re.compile(
    r"https?://[^\s\"'<>]+",
    re.IGNORECASE,
)

HTML_HREF_RE = re.compile(
    r"""href\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


class NonRetryableImapError(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _decode_mime_header(v: str) -> str:
    if not v:
        return ""
    try:
        return str(make_header(decode_header(v)))
    except Exception:
        return v


def _split_contains(value: Optional[str]) -> List[str]:
    if not value:
        return []
    out: List[str] = []
    for x in str(value).split(";"):
        x = (x or "").strip()
        if x:
            out.append(x.lower())
    return out


def _allowed_exts() -> List[str]:
    raw = getattr(settings, "IMAP_ALLOWED_EXTENSIONS", None)
    if not raw:
        return []
    out: List[str] = []
    for x in str(raw).split(";"):
        x = (x or "").strip().lower()
        if not x:
            continue
        if not x.startswith("."):
            x = "." + x
        out.append(x)
    return out


def _match_filters(subject: str, from_addr: str) -> bool:
    subj = (subject or "").lower()
    frm = (from_addr or "").lower()

    subj_filters = _split_contains(getattr(settings, "IMAP_SUBJECT_CONTAINS", None))
    from_filters = _split_contains(getattr(settings, "IMAP_FROM_CONTAINS", None))

    if subj_filters and not any(x in subj for x in subj_filters):
        return False

    if from_filters and not any(x in frm for x in from_filters):
        return False

    return True


def _imap_connect() -> imaplib.IMAP4:
    if not settings.IMAP_HOST or not settings.IMAP_USERNAME or not settings.IMAP_PASSWORD:
        raise RuntimeError("IMAP credentials are not configured")

    if settings.IMAP_SSL:
        client = imaplib.IMAP4_SSL(
            settings.IMAP_HOST,
            settings.IMAP_PORT,
            timeout=settings.IMAP_TIMEOUT_SECONDS,
        )
    else:
        client = imaplib.IMAP4(
            settings.IMAP_HOST,
            settings.IMAP_PORT,
            timeout=settings.IMAP_TIMEOUT_SECONDS,
        )

    client.login(settings.IMAP_USERNAME, settings.IMAP_PASSWORD)
    return client


def _iter_attachments(msg: Message) -> List[Tuple[str, str, bytes]]:
    out: List[Tuple[str, str, bytes]] = []
    exts = _allowed_exts()

    for part in msg.walk():
        if part.is_multipart():
            continue

        disp = (part.get("Content-Disposition") or "").lower()
        if ("attachment" not in disp) and ("inline" not in disp):
            continue

        filename = part.get_filename() or ""
        if not filename:
            continue

        payload = part.get_payload(decode=True) or b""
        if not payload:
            continue

        fn_low = filename.lower()
        if exts and not any(fn_low.endswith(ext) for ext in exts):
            continue

        content_type = part.get_content_type() or "application/octet-stream"
        out.append((filename, content_type, payload))

        if len(out) >= settings.IMAP_MAX_ATTACHMENTS_PER_MESSAGE:
            break

    return out


def _html_to_text(value: str) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n", text)
    text = re.sub(r"(?is)</div\s*>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def _extract_links_from_html(value: str) -> List[str]:
    if not value:
        return []

    raw = html.unescape(value)
    out: List[str] = []

    for m in HTML_HREF_RE.finditer(raw):
        url = (m.group(1) or "").strip()
        if not url:
            continue
        if url.lower().startswith(("http://", "https://")):
            out.append(url)

    return out


def _get_message_text_and_links(msg: Message) -> Tuple[str, List[str]]:
    chunks: List[str] = []
    links: List[str] = []

    for part in msg.walk():
        if part.is_multipart():
            continue

        ctype = (part.get_content_type() or "").lower()
        if ctype not in ("text/plain", "text/html"):
            continue

        try:
            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="ignore")

            if ctype == "text/html":
                links.extend(_extract_links_from_html(decoded))
                decoded = _html_to_text(decoded)

            if decoded:
                chunks.append(decoded)
        except Exception:
            continue

    text = "\n".join(chunks)

    for m in GENERIC_URL_RE.finditer(text):
        links.append(m.group(0).strip())

    seen = set()
    uniq_links: List[str] = []
    for url in links:
        norm = url.strip()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        uniq_links.append(norm)

    return text, uniq_links


def _find_sber_link(text: str, links: Optional[List[str]] = None) -> Optional[str]:
    candidates: List[str] = []

    if links:
        for url in links:
            cleaned = html.unescape((url or "").strip()).rstrip(").,;")
            if cleaned:
                direct = extract_sber_link(cleaned)
                if direct:
                    candidates.append(direct)

    if text:
        direct = extract_sber_link(text)
        if direct:
            candidates.append(direct)

        for m in GENERIC_URL_RE.finditer(text):
            cleaned = html.unescape((m.group(0) or "").strip()).rstrip(").,;")
            if cleaned:
                direct = extract_sber_link(cleaned)
                if direct:
                    candidates.append(direct)

    if not candidates:
        return None

    uniq: List[str] = []
    seen = set()
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)

    return uniq[0]


def _get_sync_engine():
    url = os.getenv("DATABASE_URL_SYNC") or settings.database_sync_url
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return create_engine(url, pool_pre_ping=True, future=True)


_engine = _get_sync_engine()
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def _notify(db, tenant_id, user_id, title: str, message: str, ntype: str, payload: Optional[dict] = None):
    if not user_id:
        return

    db.add(
        Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=ntype,
            payload=payload or {},
            related_type="email_ingest",
            related_id=None,
        )
    )


def _latest_user_id(db, tenant_id: str) -> Optional[str]:
    return (
        db.execute(
            select(User.id)
            .where(
                User.tenant_id == tenant_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
            .order_by(User.created_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )


def _job_exists(db, tenant_id: str, bank_account_id: str, file_sha256: str) -> bool:
    q = (
        select(ImportJob.id)
        .where(
            ImportJob.tenant_id == tenant_id,
            ImportJob.deleted_at.is_(None),
            ImportJob.file_sha256 == file_sha256,
            (ImportJob.meta["bank_account_id"].astext == bank_account_id),
        )
        .limit(1)
    )
    return db.execute(q).first() is not None


def _message_is_terminally_processed(db, tenant_id: str, mailbox: str, message_uid: str) -> bool:
    q = (
        select(EmailIngestEvent.id)
        .where(
            EmailIngestEvent.tenant_id == tenant_id,
            EmailIngestEvent.mailbox == mailbox,
            EmailIngestEvent.message_uid == str(message_uid),
            EmailIngestEvent.deleted_at.is_(None),
            or_(
                EmailIngestEvent.status.in_(["SUCCESS", "SKIPPED"]),
                and_(EmailIngestEvent.processed.is_(True), EmailIngestEvent.status.is_(None)),
            ),
        )
        .limit(1)
    )
    return db.execute(q).first() is not None


def _register_ingest_event(
    db,
    tenant_id: str,
    mailbox: str,
    message_uid: str,
    sha256_value: str,
    attachment_name: str,
    attachment_mime: str,
    attachment_size: int,
    meta: dict,
) -> Optional[EmailIngestEvent]:
    stmt = (
        insert(EmailIngestEvent)
        .values(
            tenant_id=tenant_id,
            mailbox=mailbox,
            message_uid=str(message_uid),
            attachment_sha256=sha256_value,
            attachment_name=attachment_name,
            attachment_mime=attachment_mime,
            attachment_size=str(attachment_size),
            status="PENDING",
            meta=meta,
            processed=False,
        )
        .on_conflict_do_nothing(constraint="ux_email_ingest_tenant_mailbox_uid_sha")
        .returning(EmailIngestEvent.id)
    )

    res = db.execute(stmt)
    row = res.first()
    db.commit()

    if not row:
        return None

    event_id = row[0]
    return db.execute(select(EmailIngestEvent).where(EmailIngestEvent.id == event_id)).scalar_one_or_none()


def _update_event_status(
    db,
    event_id,
    status: str,
    processed: bool,
    error: Optional[str] = None,
    extra_meta: Optional[dict] = None,
):
    event = db.execute(select(EmailIngestEvent).where(EmailIngestEvent.id == event_id)).scalar_one_or_none()
    if not event:
        return

    meta = dict(event.meta or {})
    if extra_meta:
        meta.update(extra_meta)

    event.status = status
    event.processed = processed
    event.processed_at = _utcnow() if processed else None
    event.error = error
    event.meta = meta
    db.commit()


def _search_message_ids(client: imaplib.IMAP4) -> List[bytes]:
    mode = (settings.IMAP_SEARCH_MODE or "ALL_LAST_N").strip().upper()

    if mode == "UNSEEN":
        typ, data = client.search(None, "UNSEEN")
        if typ != "OK":
            raise RuntimeError("IMAP search UNSEEN failed")
        return data[0].split() if data and data[0] else []

    if mode == "SINCE":
        since_days = max(1, int(settings.IMAP_SEARCH_SINCE_DAYS))
        since_dt = datetime.now() - timedelta(days=since_days)
        since_str = since_dt.strftime("%d-%b-%Y")
        typ, data = client.search(None, "SINCE", since_str)
        if typ != "OK":
            raise RuntimeError(f"IMAP search SINCE failed for {since_str}")
        msg_ids = data[0].split() if data and data[0] else []
        if settings.IMAP_MAX_MESSAGES_PER_RUN > 0:
            msg_ids = msg_ids[-settings.IMAP_MAX_MESSAGES_PER_RUN :]
        return msg_ids

    if mode == "ALL_LAST_N":
        typ, data = client.search(None, "ALL")
        if typ != "OK":
            raise RuntimeError("IMAP search ALL failed")
        msg_ids = data[0].split() if data and data[0] else []
        last_n = max(1, int(settings.IMAP_LAST_N))
        msg_ids = msg_ids[-last_n:]
        if settings.IMAP_MAX_MESSAGES_PER_RUN > 0:
            msg_ids = msg_ids[-settings.IMAP_MAX_MESSAGES_PER_RUN :]
        return msg_ids

    raise RuntimeError(f"Unsupported IMAP_SEARCH_MODE: {mode}")


def _extract_message_uid(msg_id: bytes, msg_data) -> str:
    message_uid = None
    try:
        fetch_line = msg_data[0][0].decode(errors="ignore") if msg_data[0][0] else ""
        parts = fetch_line.split()
        if "UID" in parts:
            message_uid = parts[parts.index("UID") + 1].rstrip(")")
    except Exception:
        message_uid = None

    if not message_uid:
        return msg_id.decode(errors="ignore")

    return str(message_uid)


def _build_sber_import_filename(message_uid: str, result: SberDownloadResult) -> str:
    filename = (result.file_name or "").strip()
    if filename:
        return filename
    return f"Sber_{message_uid}.xlsx"


@celery_app.task(bind=True, name="app.tasks.imap_ingest.imap_poll_job", max_retries=3)
def imap_poll_job(self):
    if not settings.IMAP_ENABLED:
        return {"status": "skipped", "message": "IMAP is disabled"}

    if not settings.IMAP_TENANT_SLUG:
        raise RuntimeError("IMAP_TENANT_SLUG is required for MVP")

    bank_account_id = settings.IMAP_DEFAULT_BANK_ACCOUNT_ID
    if not bank_account_id:
        raise RuntimeError("IMAP_DEFAULT_BANK_ACCOUNT_ID is required for MVP")

    client: Optional[imaplib.IMAP4] = None
    processed = 0
    created_jobs = 0
    marked_seen = 0
    skipped_by_filter = 0
    skipped_by_ext = 0
    skipped_by_size = 0
    skipped_no_data = 0
    skipped_existing_job = 0
    skipped_existing_message = 0
    sber_link_downloaded = 0
    sber_link_failed = 0
    sber_link_gone = 0
    sber_tls_fallback_used = 0

    db = SessionLocal()
    try:
        tenant = (
            db.execute(select(Tenant).where(Tenant.slug == settings.IMAP_TENANT_SLUG).limit(1))
            .scalars()
            .first()
        )
        if not tenant:
            raise RuntimeError(f"Tenant not found by slug: {settings.IMAP_TENANT_SLUG}")

        user_id = _latest_user_id(db, tenant.id)

        client = _imap_connect()

        typ, _ = client.select(settings.IMAP_MAILBOX)
        if typ != "OK":
            raise RuntimeError(f"Failed to select mailbox: {settings.IMAP_MAILBOX}")

        msg_ids = _search_message_ids(client)
        if not msg_ids:
            return {
                "status": "ok",
                "processed": 0,
                "created_jobs": 0,
                "marked_seen": 0,
                "skipped": {
                    "filter": 0,
                    "ext": 0,
                    "size": 0,
                    "existing_job": 0,
                    "existing_message": 0,
                },
                "sber": {
                    "downloaded": 0,
                    "gone": 0,
                    "failed": 0,
                    "tls_fallback_used": 0,
                },
            }

        exts = _allowed_exts()

        for msg_id in reversed(msg_ids):
            typ, msg_data = client.fetch(msg_id, "(RFC822 UID)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue

            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject = _decode_mime_header(msg.get("Subject", "") or "")
            from_addr = _decode_mime_header(msg.get("From", "") or "")

            if not _match_filters(subject, from_addr):
                skipped_by_filter += 1
                continue

            message_uid = _extract_message_uid(msg_id, msg_data)

            if _message_is_terminally_processed(db, tenant.id, settings.IMAP_MAILBOX, message_uid):
                skipped_existing_message += 1
                continue

            atts = _iter_attachments(msg)
            created_any_for_msg = False

            for filename, content_type, payload in atts:
                if not payload:
                    skipped_no_data += 1
                    continue

                if exts:
                    fn_low = filename.lower()
                    if not any(fn_low.endswith(ext) for ext in exts):
                        skipped_by_ext += 1
                        continue

                if len(payload) > settings.IMAP_MAX_ATTACHMENT_BYTES:
                    skipped_by_size += 1
                    continue

                sha = sha256_bytes(payload)

                event = _register_ingest_event(
                    db=db,
                    tenant_id=tenant.id,
                    mailbox=settings.IMAP_MAILBOX,
                    message_uid=message_uid,
                    sha256_value=sha,
                    attachment_name=filename,
                    attachment_mime=content_type,
                    attachment_size=len(payload),
                    meta={
                        "subject": subject,
                        "from": from_addr,
                        "imap_message_id": msg_id.decode(errors="ignore"),
                        "source_type": "attachment",
                    },
                )
                if not event:
                    continue

                if _job_exists(db, tenant.id, bank_account_id, sha):
                    skipped_existing_job += 1
                    _update_event_status(
                        db,
                        event.id,
                        status="SKIPPED",
                        processed=True,
                        extra_meta={"skip_reason": "job_exists"},
                    )
                    continue

                s3_key = f"bank/{tenant.id}/{_utcnow().strftime('%Y%m%d')}/imap_{sha}_{filename}"
                ref = put_bytes(s3_key, payload, content_type=content_type)

                job = ImportJob(
                    tenant_id=tenant.id,
                    user_id=user_id,
                    source="email_imap",
                    file_name=filename,
                    file_mime=content_type,
                    file_size=len(payload),
                    s3_bucket=ref.bucket,
                    s3_key=ref.key,
                    file_sha256=sha,
                    status="PENDING",
                    meta={
                        "bank_account_id": bank_account_id,
                        "imap": {
                            "mailbox": settings.IMAP_MAILBOX,
                            "message_uid": str(message_uid),
                            "subject": subject,
                            "from": from_addr,
                        },
                    },
                )

                db.add(job)
                db.commit()
                db.refresh(job)

                _update_event_status(
                    db,
                    event.id,
                    status="SUCCESS",
                    processed=True,
                    extra_meta={"job_id": str(job.id)},
                )

                import_bank_statement_job.delay(str(job.id))
                created_jobs += 1
                processed += 1
                created_any_for_msg = True

            if not atts:
                text, extracted_links = _get_message_text_and_links(msg)
                link = _find_sber_link(text, extracted_links)

                if link:
                    try:
                        result = download_sber_report(
                            link,
                            timeout=int(settings.SBER_DOWNLOAD_TIMEOUT_SECONDS),
                            ca_file=(settings.SBER_CA_CERT_PATH or "").strip() or None,
                            insecure_skip_verify=not bool(settings.SBER_TLS_VERIFY),
                        )

                        data_bytes = result.body
                        if not data_bytes:
                            raise NonRetryableImapError("SBER download returned empty body")

                        if len(data_bytes) > settings.IMAP_MAX_ATTACHMENT_BYTES:
                            raise NonRetryableImapError(
                                f"SBER download too large: {len(data_bytes)} bytes"
                            )

                        if not (len(data_bytes) >= 4 and data_bytes[:4] == b"PK\x03\x04"):
                            raise NonRetryableImapError(
                                "SBER download is not XLSX (PK signature missing)"
                            )

                        sha = sha256_bytes(data_bytes)
                        dl_name = _build_sber_import_filename(message_uid, result)
                        content_type = (
                            result.content_type
                            or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                        event = _register_ingest_event(
                            db=db,
                            tenant_id=tenant.id,
                            mailbox=settings.IMAP_MAILBOX,
                            message_uid=message_uid,
                            sha256_value=sha,
                            attachment_name=dl_name,
                            attachment_mime=content_type,
                            attachment_size=len(data_bytes),
                            meta={
                                "subject": subject,
                                "from": from_addr,
                                "imap_message_id": msg_id.decode(errors="ignore"),
                                "sber_link": link,
                                "source_type": "sber_link",
                                "links_found": extracted_links[:20],
                                "text_preview": text[:1000] if text else "",
                                "tls_mode": "verified" if bool(settings.SBER_TLS_VERIFY) else "insecure_skip_verify",
                                "tls_fallback_used": bool(result.tls_fallback_used),
                                "sber_http_status": int(result.http_status),
                            },
                        )

                        if event is None:
                            skipped_existing_message += 1
                        else:
                            if _job_exists(db, tenant.id, bank_account_id, sha):
                                skipped_existing_job += 1
                                _update_event_status(
                                    db,
                                    event.id,
                                    status="SKIPPED",
                                    processed=True,
                                    extra_meta={"skip_reason": "job_exists"},
                                )
                            else:
                                s3_key = f"bank/{tenant.id}/{_utcnow().strftime('%Y%m%d')}/imap_{sha}_{dl_name}"
                                ref = put_bytes(s3_key, data_bytes, content_type=content_type)

                                job = ImportJob(
                                    tenant_id=tenant.id,
                                    user_id=user_id,
                                    source="email_imap",
                                    file_name=dl_name,
                                    file_mime=content_type,
                                    file_size=len(data_bytes),
                                    s3_bucket=ref.bucket,
                                    s3_key=ref.key,
                                    file_sha256=sha,
                                    status="PENDING",
                                    meta={
                                        "bank_account_id": bank_account_id,
                                        "imap": {
                                            "mailbox": settings.IMAP_MAILBOX,
                                            "message_uid": str(message_uid),
                                            "subject": subject,
                                            "from": from_addr,
                                            "sber_link": link,
                                            "tls_mode": "verified" if bool(settings.SBER_TLS_VERIFY) else "insecure_skip_verify",
                                            "tls_fallback_used": bool(result.tls_fallback_used),
                                            "sber_http_status": int(result.http_status),
                                        },
                                    },
                                )

                                db.add(job)
                                db.commit()
                                db.refresh(job)

                                _update_event_status(
                                    db,
                                    event.id,
                                    status="SUCCESS",
                                    processed=True,
                                    extra_meta={
                                        "job_id": str(job.id),
                                        "tls_mode": "verified" if bool(settings.SBER_TLS_VERIFY) else "insecure_skip_verify",
                                        "tls_fallback_used": bool(result.tls_fallback_used),
                                        "sber_http_status": int(result.http_status),
                                    },
                                )

                                if result.tls_fallback_used:
                                    sber_tls_fallback_used += 1

                                import_bank_statement_job.delay(str(job.id))
                                created_jobs += 1
                                processed += 1
                                created_any_for_msg = True
                                sber_link_downloaded += 1

                    except SberLinkExpiredError as e:
                        sber_link_gone += 1
                        _notify(
                            db,
                            tenant.id,
                            user_id,
                            "IMAP: Сбер ссылка протухла",
                            f"Письмо UID={message_uid}. Ссылка истекла.",
                            "info",
                            payload={
                                "message_uid": str(message_uid),
                                "link": link,
                                "error": str(e),
                                "links_found": extracted_links[:20],
                            },
                        )
                        db.commit()

                    except SberTlsError as e:
                        sber_link_failed += 1
                        _notify(
                            db,
                            tenant.id,
                            user_id,
                            "IMAP: Сбер TLS ошибка",
                            f"Письмо UID={message_uid}. Ошибка TLS: {e}",
                            "warning",
                            payload={
                                "message_uid": str(message_uid),
                                "link": link,
                                "error": str(e),
                                "links_found": extracted_links[:20],
                                "text_preview": text[:1000] if text else "",
                                "tls": {
                                    "verify": bool(settings.SBER_TLS_VERIFY),
                                    "ca_path": settings.SBER_CA_CERT_PATH,
                                },
                            },
                        )
                        db.commit()

                    except SberDnsError as e:
                        sber_link_failed += 1
                        _notify(
                            db,
                            tenant.id,
                            user_id,
                            "IMAP: Сбер DNS ошибка",
                            f"Письмо UID={message_uid}. Ошибка DNS: {e}",
                            "warning",
                            payload={
                                "message_uid": str(message_uid),
                                "link": link,
                                "error": str(e),
                                "links_found": extracted_links[:20],
                                "text_preview": text[:1000] if text else "",
                            },
                        )
                        db.commit()

                    except SberTimeoutError as e:
                        sber_link_failed += 1
                        _notify(
                            db,
                            tenant.id,
                            user_id,
                            "IMAP: Сбер таймаут",
                            f"Письмо UID={message_uid}. Таймаут: {e}",
                            "warning",
                            payload={
                                "message_uid": str(message_uid),
                                "link": link,
                                "error": str(e),
                                "links_found": extracted_links[:20],
                                "text_preview": text[:1000] if text else "",
                            },
                        )
                        db.commit()

                    except (SberHttpError, SberEmptyBodyError, SberDownloadError) as e:
                        sber_link_failed += 1
                        _notify(
                            db,
                            tenant.id,
                            user_id,
                            "IMAP: Сбер ссылка не скачалась",
                            f"Письмо UID={message_uid}. Ошибка: {e}",
                            "warning",
                            payload={
                                "message_uid": str(message_uid),
                                "link": link,
                                "error": str(e),
                                "links_found": extracted_links[:20],
                                "text_preview": text[:1000] if text else "",
                            },
                        )
                        db.commit()

                    except NonRetryableImapError as e:
                        sber_link_failed += 1
                        _notify(
                            db,
                            tenant.id,
                            user_id,
                            "IMAP: Сбер ссылка невалидна",
                            f"Письмо UID={message_uid}. {e}",
                            "warning",
                            payload={
                                "message_uid": str(message_uid),
                                "link": link,
                                "error": str(e),
                                "links_found": extracted_links[:20],
                                "text_preview": text[:1000] if text else "",
                            },
                        )
                        db.commit()

                    except Exception as e:
                        sber_link_failed += 1
                        _notify(
                            db,
                            tenant.id,
                            user_id,
                            "IMAP: Сбер ссылка не скачалась",
                            f"Письмо UID={message_uid}. Ошибка: {e}",
                            "warning",
                            payload={
                                "message_uid": str(message_uid),
                                "link": link,
                                "error": str(e),
                                "links_found": extracted_links[:20],
                                "text_preview": text[:1000] if text else "",
                            },
                        )
                        db.commit()
                else:
                    _notify(
                        db,
                        tenant.id,
                        user_id,
                        "IMAP: письмо без вложений",
                        (
                            f"Письмо UID={message_uid} прошло фильтры, но нет .xlsx вложений и нет ссылки Сбер. "
                            f"links_found={len(extracted_links)}"
                        ),
                        "info",
                        payload={
                            "message_uid": str(message_uid),
                            "from": from_addr,
                            "subject": subject,
                            "links_found": extracted_links[:20],
                            "text_preview": text[:1000] if text else "",
                        },
                    )
                    db.commit()

            should_mark_seen = True
            if settings.IMAP_MARK_SEEN_ONLY_ON_SUCCESS:
                should_mark_seen = created_any_for_msg

            if should_mark_seen:
                try:
                    client.store(msg_id, "+FLAGS", r"(\Seen)")
                    marked_seen += 1
                except Exception:
                    pass

        _notify(
            db,
            tenant.id,
            user_id,
            "IMAP: проверка почты выполнена",
            (
                f"processed={processed}, created_jobs={created_jobs}, marked_seen={marked_seen}. "
                f"skipped(filter={skipped_by_filter}, ext={skipped_by_ext}, size={skipped_by_size}, "
                f"existing_job={skipped_existing_job}, existing_message={skipped_existing_message}). "
                f"sber(downloaded={sber_link_downloaded}, gone={sber_link_gone}, "
                f"failed={sber_link_failed}, tls_fallback_used={sber_tls_fallback_used})."
            ),
            "info",
            payload={
                "processed": processed,
                "created_jobs": created_jobs,
                "marked_seen": marked_seen,
                "search_mode": settings.IMAP_SEARCH_MODE,
                "last_n": settings.IMAP_LAST_N,
                "skipped": {
                    "filter": skipped_by_filter,
                    "ext": skipped_by_ext,
                    "size": skipped_by_size,
                    "existing_job": skipped_existing_job,
                    "existing_message": skipped_existing_message,
                },
                "sber": {
                    "downloaded": sber_link_downloaded,
                    "gone": sber_link_gone,
                    "failed": sber_link_failed,
                    "tls_fallback_used": sber_tls_fallback_used,
                },
                "tls": {
                    "verify": settings.SBER_TLS_VERIFY,
                    "ca_path": settings.SBER_CA_CERT_PATH,
                },
            },
        )
        db.commit()

        return {
            "status": "ok",
            "processed": processed,
            "created_jobs": created_jobs,
            "marked_seen": marked_seen,
            "search_mode": settings.IMAP_SEARCH_MODE,
            "skipped": {
                "filter": skipped_by_filter,
                "ext": skipped_by_ext,
                "size": skipped_by_size,
                "existing_job": skipped_existing_job,
                "existing_message": skipped_existing_message,
            },
            "sber": {
                "downloaded": sber_link_downloaded,
                "gone": sber_link_gone,
                "failed": sber_link_failed,
                "tls_fallback_used": sber_tls_fallback_used,
            },
        }

    except NonRetryableImapError as exc:
        try:
            db.rollback()
        except Exception:
            pass

        try:
            tenant2 = (
                db.execute(select(Tenant).where(Tenant.slug == settings.IMAP_TENANT_SLUG).limit(1))
                .scalars()
                .first()
            )
            if tenant2:
                user2 = _latest_user_id(db, tenant2.id)
                _notify(
                    db,
                    tenant2.id,
                    user2,
                    "IMAP: контролируемая ошибка",
                    str(exc),
                    "warning",
                    payload={"error": str(exc)},
                )
                db.commit()
        except Exception:
            pass

        return {"status": "failed", "error": str(exc)}

    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass

        try:
            tenant2 = (
                db.execute(select(Tenant).where(Tenant.slug == settings.IMAP_TENANT_SLUG).limit(1))
                .scalars()
                .first()
            )
            if tenant2:
                user2 = _latest_user_id(db, tenant2.id)
                _notify(
                    db,
                    tenant2.id,
                    user2,
                    "IMAP: ошибка",
                    str(exc),
                    "error",
                    payload={"error": str(exc)},
                )
                db.commit()
        except Exception:
            pass

        raise self.retry(exc=exc, countdown=60)

    finally:
        try:
            db.close()
        except Exception:
            pass
        try:
            if client:
                client.logout()
        except Exception:
            pass