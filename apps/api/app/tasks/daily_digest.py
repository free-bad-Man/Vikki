from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, func, case

from celery_app import celery_app
from app.database import sync_session_maker
from app.models.tenant import Tenant
from app.models.user import User
from app.models.transaction import Transaction
from app.models.notification import Notification


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _tz_name() -> str:
    return os.getenv("DAILY_DIGEST_TIMEZONE", "Europe/Moscow")


def _msk_yesterday_window_utc() -> tuple[datetime, datetime, str]:
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(_tz_name())
    now_local = datetime.now(tz)
    yday_local = (now_local.date() - timedelta(days=1))
    start_local = datetime(yday_local.year, yday_local.month, yday_local.day, 0, 0, 0, tzinfo=tz)
    end_local = start_local + timedelta(days=1)

    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    return start_utc, end_utc, yday_local.isoformat()


def _send_telegram(text: str) -> Optional[str]:
    if not _env_bool("TELEGRAM_ENABLED", False):
        return None

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return "telegram disabled: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}

    try:
        import requests  # type: ignore

        r = requests.post(url, json=payload, timeout=15)
        if r.status_code >= 400:
            return f"telegram http {r.status_code}: {r.text[:300]}"
        return None
    except Exception:
        try:
            import json
            import urllib.request

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status >= 400:
                    return f"telegram http {resp.status}"
            return None
        except Exception as e:
            return f"telegram error: {repr(e)}"


def _fmt_money(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ")


@celery_app.task(bind=True, name="app.tasks.daily_digest.daily_digest_job", max_retries=3)
def daily_digest_job(self):
    if not _env_bool("DAILY_DIGEST_ENABLED", False):
        return {"status": "skipped", "message": "DAILY_DIGEST is disabled"}

    tenant_slug = os.getenv("DAILY_DIGEST_TENANT_SLUG", "").strip()
    if not tenant_slug:
        return {"status": "skipped", "message": "DAILY_DIGEST_TENANT_SLUG is empty"}

    start_utc, end_utc, digest_date = _msk_yesterday_window_utc()

    with sync_session_maker() as db:
        tenant = db.execute(select(Tenant).where(Tenant.slug == tenant_slug)).scalar_one_or_none()
        if not tenant:
            return {"status": "error", "message": f"tenant not found: {tenant_slug}"}

        tenant_id = str(tenant.id)

        # Нужен user_id (NOT NULL в notifications)
        user = db.execute(
            select(User)
            .where(
                User.tenant_id == tenant_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
            .order_by(User.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if not user:
            return {"status": "error", "message": f"no active user for tenant {tenant_slug}"}

        user_id = str(user.id)

        # Идемпотентность: если уже есть digest notification за digest_date — выходим
        exists = db.execute(
            select(Notification.id).where(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
                Notification.related_type == "daily_digest",
                (Notification.payload["digest_date"].astext == digest_date),
            )
        ).first()
        if exists:
            return {"status": "skipped", "message": f"digest already sent for {digest_date}", "digest_date": digest_date}

        income_expr = case((Transaction.transaction_type == "incoming", Transaction.amount), else_=0)
        expense_expr = case((Transaction.transaction_type == "outgoing", Transaction.amount), else_=0)
        inc_cnt_expr = case((Transaction.transaction_type == "incoming", 1), else_=0)
        out_cnt_expr = case((Transaction.transaction_type == "outgoing", 1), else_=0)

        income, expense, ops, inc_cnt, out_cnt = db.execute(
            select(
                func.coalesce(func.sum(income_expr), 0),
                func.coalesce(func.sum(expense_expr), 0),
                func.count(),
                func.coalesce(func.sum(inc_cnt_expr), 0),
                func.coalesce(func.sum(out_cnt_expr), 0),
            ).where(
                Transaction.tenant_id == tenant_id,
                Transaction.deleted_at.is_(None),
                Transaction.occurred_at >= start_utc,
                Transaction.occurred_at < end_utc,
            )
        ).one()

        income = float(income or 0)
        expense = float(expense or 0)
        ops = int(ops or 0)
        inc_cnt = int(inc_cnt or 0)
        out_cnt = int(out_cnt or 0)
        net = income - expense

        top_cp = db.execute(
            select(
                Transaction.counterparty_name,
                func.sum(Transaction.amount).label("total"),
                func.count().label("ops"),
            )
            .where(
                Transaction.tenant_id == tenant_id,
                Transaction.deleted_at.is_(None),
                Transaction.occurred_at >= start_utc,
                Transaction.occurred_at < end_utc,
                Transaction.counterparty_name.isnot(None),
                Transaction.counterparty_name != "",
            )
            .group_by(Transaction.counterparty_name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(5)
        ).all()

        top_purposes = db.execute(
            select(
                Transaction.description,
                func.sum(Transaction.amount).label("total"),
                func.count().label("ops"),
            )
            .where(
                Transaction.tenant_id == tenant_id,
                Transaction.deleted_at.is_(None),
                Transaction.occurred_at >= start_utc,
                Transaction.occurred_at < end_utc,
                Transaction.description.isnot(None),
                Transaction.description != "",
            )
            .group_by(Transaction.description)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(5)
        ).all()

        lines: List[str] = []
        lines.append(f"📊 Daily Digest за {digest_date} (MSK)")
        lines.append(f"Операций: {ops} (поступлений {inc_cnt}, списаний {out_cnt})")
        lines.append(f"Поступления: {_fmt_money(income)}")
        lines.append(f"Списания: {_fmt_money(expense)}")
        lines.append(f"Net: {_fmt_money(net)}")

        if top_cp:
            lines.append("")
            lines.append("🏷 Топ контрагентов:")
            for name, total, nops in top_cp:
                lines.append(f"- {name}: {_fmt_money(float(total or 0))} ({int(nops)} ops)")

        if top_purposes:
            lines.append("")
            lines.append("🧾 Топ назначений:")
            for desc, total, nops in top_purposes:
                s = str(desc or "")
                short = (s[:80] + "…") if len(s) > 80 else s
                lines.append(f"- {short}: {_fmt_money(float(total or 0))} ({int(nops)} ops)")

        text = "\n".join(lines)

        notif = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title=f"Daily Digest {digest_date}",
            message=text,
            notification_type="digest",
            payload={
                "digest_date": digest_date,
                "tz": _tz_name(),
                "window_utc": {"from": start_utc.isoformat(), "to": end_utc.isoformat()},
                "summary": {
                    "income": income,
                    "expense": expense,
                    "net": net,
                    "operations": ops,
                    "incoming_count": inc_cnt,
                    "outgoing_count": out_cnt,
                },
                "top_counterparties": [
                    {"name": (n or ""), "total": float(t or 0), "ops": int(o)} for (n, t, o) in top_cp
                ],
                "top_purposes": [
                    {"name": (d or ""), "total": float(t or 0), "ops": int(o)} for (d, t, o) in top_purposes
                ],
                "telegram": {"enabled": _env_bool("TELEGRAM_ENABLED", False)},
                "target_user_id": user_id,
            },
            related_type="daily_digest",
            related_id=digest_date,
        )
        db.add(notif)
        db.commit()

        tg_err = _send_telegram(text)
        if tg_err:
            notif.payload = dict(notif.payload or {})
            notif.payload["telegram"] = {"enabled": True, "error": tg_err}
            db.add(notif)
            db.commit()

        return {"status": "success", "digest_date": digest_date, "ops": ops, "user_id": user_id, "telegram_error": tg_err}