"""Gmail ingest — mock sync by default; optional Google OAuth when credentials are set.

Mock mode injects demo Gmail-like messages into the inbox so the portfolio demo
works offline without secrets. Real mode uses a refresh token + client credentials
to list recent inbox messages via Gmail API (messages.list + messages.get).

OAuth setup (no secrets committed): see README "Gmail OAuth" and
scripts/gmail_oauth_refresh_token.py.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ActivityLog, Email
from app.services.attention import apply_attention, catalog_prices, recompute_all

logger = logging.getLogger(__name__)

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

# Pool of demo messages that "arrive" on each mock sync (message_id must be stable
# so repeated syncs are idempotent). Content is varied for attention ranking demos.
_MOCK_NOW = datetime.now(timezone.utc)

MOCK_GMAIL_POOL: list[dict[str, Any]] = [
    {
        "message_id": "gmail-mock-004-pump-rfq",
        "from_address": "buyer@riverbend-plants.example",
        "from_name": "Jordan Blake",
        "subject": "URGENT RFQ — Centrifugal Process Pump C2 × 2 — ASAP",
        "body": (
            "Hello Northwind,\n\n"
            "URGENT — production halted. Please quote ASAP:\n"
            "- 2 × Centrifugal Process Pump C2 (NW-PMP-C2)\n"
            "- 4 × Mechanical Seal Rebuild Kit (NW-SEAL-KIT)\n\n"
            "Need delivery to Riverbend Plants, Cleveland OH within 3 weeks.\n"
            "This is time-sensitive — escalate if needed.\n\n"
            "Jordan Blake\nPurchasing"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=1),
    },
    {
        "message_id": "gmail-mock-005-idler-rfq",
        "from_address": "maint@coastal-agg.example",
        "from_name": "Sam Ortiz",
        "subject": "RFQ: Conveyor idler rollers — 80 units",
        "body": (
            "Team,\n\n"
            "Requesting quotation for 80 × Conveyor Idler Roller 4-inch (NW-CNV-IDL).\n"
            "Also include unit price for NW-BRG-6205 bearings (qty 50) as optional add-on.\n\n"
            "Thanks,\nSam Ortiz\nCoastal Aggregates"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=8),
    },
    {
        "message_id": "gmail-mock-006-vfd-followup",
        "from_address": "ops@summit-packaging.example",
        "from_name": "Marcus Chen",
        "subject": "Follow-up: additional VFD for line 2",
        "body": (
            "Hi again,\n\n"
            "Can you also quote 2 × 7.5 HP Variable Frequency Drive (NW-VFD-7)\n"
            "for our second packaging line?\n\n"
            "Marcus Chen\nSummit Packaging LLC"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=12),
    },
    {
        "message_id": "gmail-mock-007-escalation",
        "from_address": "vp.ops@midwest-steel.example",
        "from_name": "Dana Okonkwo",
        "subject": "Escalation: overdue quote on NW-MTR-3HP — CEO reviewing suppliers",
        "body": (
            "Northwind,\n\n"
            "This is an escalation / final notice. We requested a quote two weeks ago for\n"
            "12 × NW-MTR-3HP motors (~$8,200). Our CEO is reviewing suppliers Friday.\n"
            "Please respond urgently or we will cancel the RFQ.\n\n"
            "Dana Okonkwo\nVP Operations — Midwest Steel"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=4),
    },
    {
        "message_id": "gmail-mock-008-low-noise",
        "from_address": "noreply@parts-partner.example",
        "from_name": "Parts Partner",
        "subject": "Your monthly account statement is ready",
        "body": (
            "Hi,\n\nYour statement for last month is attached in the portal.\n"
            "No reply needed.\n\n— Parts Partner Billing"
        ),
        "received_at": _MOCK_NOW - timedelta(days=3),
    },
]


def gmail_connection_status() -> dict[str, Any]:
    settings = get_settings()
    real_ready = bool(
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_refresh_token
    )
    requested = (settings.gmail_mode or "mock").strip().lower()
    if requested == "oauth" and real_ready:
        mode = "oauth"
        reason = None
        detail = "Live Gmail API via refresh token (messages.list + get)"
    elif requested == "oauth" and not real_ready:
        mode = "mock"
        reason = (
            "GMAIL_MODE=oauth but GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / "
            "GOOGLE_REFRESH_TOKEN incomplete — using mock"
        )
        detail = reason
    else:
        mode = "mock"
        reason = None
        detail = "Demo sync injects seeded Gmail-like messages (no secrets required)"

    return {
        "mode": mode,
        "connected": mode == "oauth",
        "label": "Connected" if mode == "oauth" else "Mock",
        "detail": detail,
        "oauth_configured": real_ready,
        "requested_mode": requested,
        "scope": GMAIL_READONLY_SCOPE,
        "hint": (
            None
            if mode == "oauth"
            else (
                "Set GMAIL_MODE=oauth and Google OAuth credentials in backend/.env; "
                "see README + scripts/gmail_oauth_refresh_token.py"
            )
        ),
    }


async def sync_inbox(db: Session) -> dict[str, Any]:
    status = gmail_connection_status()
    if status["mode"] == "oauth":
        try:
            result = await _sync_oauth(db)
        except Exception as exc:  # noqa: BLE001 — fall back so demos never brick
            logger.exception("Gmail OAuth sync failed; falling back to mock")
            result = _sync_mock(db)
            result["warning"] = f"OAuth sync failed ({exc}); used mock instead"
            result["mode"] = "mock"
    else:
        result = _sync_mock(db)

    # Age-sensitive factors: refresh scores for the whole inbox after sync
    scored = recompute_all(db)
    result["attention_rescored"] = scored
    result["status"] = gmail_connection_status()
    # Refresh ORM instances after recompute
    if result.get("emails"):
        ids = [e.id for e in result["emails"]]
        result["emails"] = db.query(Email).filter(Email.id.in_(ids)).all() if ids else []
    return result


def _persist_new_email(db: Session, *, fields: dict[str, Any], catalog: dict[str, float]) -> Email:
    email = Email(**fields)
    apply_attention(email, catalog=catalog)
    db.add(email)
    return email


def _sync_mock(db: Session) -> dict[str, Any]:
    created: list[Email] = []
    skipped = 0
    catalog = catalog_prices(db)
    for row in MOCK_GMAIL_POOL:
        existing = db.query(Email).filter(Email.message_id == row["message_id"]).first()
        if existing:
            skipped += 1
            continue
        email = _persist_new_email(
            db,
            fields={
                "message_id": row["message_id"],
                "from_address": row["from_address"],
                "from_name": row["from_name"],
                "to_address": "quotes@northwind-industrial.example",
                "subject": row["subject"],
                "body": row["body"],
                "received_at": row.get("received_at") or datetime.now(timezone.utc),
                "status": "unread",
            },
            catalog=catalog,
        )
        created.append(email)

    if created:
        db.add(
            ActivityLog(
                kind="gmail_sync",
                message=f"Mock Gmail sync imported {len(created)} message(s)",
                meta={
                    "mode": "mock",
                    "imported": len(created),
                    "skipped": skipped,
                    "message_ids": [e.message_id for e in created],
                },
            )
        )
    else:
        db.add(
            ActivityLog(
                kind="gmail_sync",
                message="Mock Gmail sync — inbox already up to date",
                meta={"mode": "mock", "imported": 0, "skipped": skipped},
            )
        )
    db.commit()
    for e in created:
        db.refresh(e)

    return {
        "mode": "mock",
        "imported": len(created),
        "skipped": skipped,
        "emails": created,
        "status": gmail_connection_status(),
    }


async def _sync_oauth(db: Session) -> dict[str, Any]:
    settings = get_settings()
    token = await _refresh_access_token(
        settings.google_client_id or "",
        settings.google_client_secret or "",
        settings.google_refresh_token or "",
    )
    messages = await _list_gmail_messages(token, max_results=25)
    created: list[Email] = []
    skipped = 0
    catalog = catalog_prices(db)
    for msg in messages:
        mid = f"gmail-{msg['id']}"
        existing = db.query(Email).filter(Email.message_id == mid).first()
        if existing:
            skipped += 1
            continue
        parsed = _parse_gmail_message(msg)
        email = _persist_new_email(
            db,
            fields={
                "message_id": mid,
                "from_address": parsed["from_address"],
                "from_name": parsed["from_name"],
                "to_address": parsed["to_address"],
                "subject": parsed["subject"],
                "body": parsed["body"],
                "received_at": parsed["received_at"],
                "status": "unread",
            },
            catalog=catalog,
        )
        created.append(email)

    db.add(
        ActivityLog(
            kind="gmail_sync",
            message=f"Gmail OAuth sync imported {len(created)} message(s)",
            meta={"mode": "oauth", "imported": len(created), "skipped": skipped},
        )
    )
    db.commit()
    for e in created:
        db.refresh(e)

    return {
        "mode": "oauth",
        "imported": len(created),
        "skipped": skipped,
        "emails": created,
        "status": gmail_connection_status(),
    }


async def _refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["access_token"]


async def _list_gmail_messages(access_token: str, max_results: int = 25) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        listing = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params={"maxResults": max_results, "q": "in:inbox"},
        )
        listing.raise_for_status()
        ids = [m["id"] for m in (listing.json().get("messages") or [])]
        out: list[dict[str, Any]] = []
        for mid in ids:
            detail = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}",
                headers=headers,
                params={"format": "full"},
            )
            detail.raise_for_status()
            out.append(detail.json())
        return out


def _header_map(payload: dict[str, Any]) -> dict[str, str]:
    headers = payload.get("headers") or []
    return {h["name"].lower(): h["value"] for h in headers if "name" in h and "value" in h}


def _extract_body(payload: dict[str, Any]) -> str:
    import base64

    if payload.get("body", {}).get("data"):
        raw = payload["body"]["data"]
        return base64.urlsafe_b64decode(raw + "==").decode("utf-8", errors="replace")
    for part in payload.get("parts") or []:
        mime = part.get("mimeType", "")
        if mime == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    for part in payload.get("parts") or []:
        nested = _extract_body(part)
        if nested:
            return nested
    return (payload.get("snippet") or "").strip()


def _parse_from(value: str) -> tuple[str, str]:
    # "Name <email@x.com>" or bare email
    if "<" in value and ">" in value:
        name = value.split("<", 1)[0].strip().strip('"')
        addr = value.split("<", 1)[1].split(">", 1)[0].strip()
        return name, addr
    return "", value.strip()


def _parse_gmail_message(msg: dict[str, Any]) -> dict[str, Any]:
    payload = msg.get("payload") or {}
    headers = _header_map(payload)
    from_name, from_address = _parse_from(headers.get("from", "unknown@example.com"))
    to_raw = headers.get("to", "quotes@northwind-industrial.example")
    _, to_address = _parse_from(to_raw) if "<" in to_raw else ("", to_raw)
    subject = headers.get("subject", "(no subject)")
    body = _extract_body(payload) or msg.get("snippet") or ""
    received_at = datetime.now(timezone.utc)
    date_hdr = headers.get("date")
    if date_hdr:
        try:
            received_at = parsedate_to_datetime(date_hdr)
        except (TypeError, ValueError, IndexError):
            pass
    internal = msg.get("internalDate")
    if internal and not date_hdr:
        try:
            received_at = datetime.fromtimestamp(int(internal) / 1000, tz=timezone.utc)
        except (TypeError, ValueError):
            pass
    return {
        "from_address": from_address or "unknown@example.com",
        "from_name": from_name,
        "to_address": to_address or "quotes@northwind-industrial.example",
        "subject": subject,
        "body": body,
        "received_at": received_at,
    }


def ingest_external_email(
    db: Session,
    *,
    from_address: str,
    subject: str,
    body: str,
    from_name: str = "",
    to_address: str = "quotes@northwind-industrial.example",
    message_id: str | None = None,
    source: str = "n8n",
) -> Email:
    """Create an inbox row from an external webhook (n8n, etc.)."""
    mid = message_id or f"{source}-{uuid4().hex[:16]}"
    # Stable-ish dedupe if caller re-posts same content without id
    if not message_id:
        digest = hashlib.sha1(f"{from_address}|{subject}|{body[:200]}".encode()).hexdigest()[:16]
        mid = f"{source}-{digest}"
        existing = db.query(Email).filter(Email.message_id == mid).first()
        if existing:
            return existing

    existing = db.query(Email).filter(Email.message_id == mid).first()
    if existing:
        return existing

    catalog = catalog_prices(db)
    email = Email(
        message_id=mid,
        from_address=from_address,
        from_name=from_name or from_address.split("@")[0],
        to_address=to_address,
        subject=subject,
        body=body,
        received_at=datetime.now(timezone.utc),
        status="unread",
    )
    apply_attention(email, catalog=catalog)
    db.add(email)
    db.add(
        ActivityLog(
            kind="webhook_ingest",
            message=f"Ingested email via {source}: {subject[:80]}",
            meta={
                "source": source,
                "from": from_address,
                "message_id": mid,
                "attention_score": email.attention_score,
                "attention_label": email.attention_label,
            },
        )
    )
    db.commit()
    db.refresh(email)
    return email
