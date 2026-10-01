"""Gmail ingest — mock sync by default; optional Google OAuth when credentials are set.

On every successful business import: classify intent + suggested action.
Optional auto-stage of full ops plans via AUTO_STAGE_ON_SYNC (default on for mock demos).
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.agent.ops_workflow import classify_email_on_ingest, run_ops_plan
from app.config import get_settings
from app.models import ActivityLog, Email
from app.services.attention import apply_attention, catalog_prices, recompute_all
from app.services.business_relevance import should_import_message

logger = logging.getLogger(__name__)

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

# Prefer Primary/ops-ish mail at the API layer; post-filter still applies.
# Excludes Promotions + Social categories (Updates kept — shipping/PO alerts often land there).
GMAIL_LIST_QUERY = (
    "in:inbox -category:promotions -category:social "
    "-from:redditmail.com -from:linkedin.com -from:substack.com "
    "-from:medium.com -from:mail.medium.com -from:notifications.github.com "
    "-from:bseindia.com -from:nseindia.com -from:unstop.com "
    "-from:dare2compete.com -from:naukri.com -from:indeed.com"
)
_MOCK_NOW = datetime.now(timezone.utc)

# Varied B2B intents for agency-grade demo coverage
MOCK_GMAIL_POOL: list[dict[str, Any]] = [
    {
        "message_id": "gmail-mock-004-pump-rfq",
        "from_address": "buyer@riverbend-plants.example",
        "from_name": "Jordan Blake",
        "subject": "URGENT RFQ — Centrifugal Process Pump C2 × 2 — ASAP",
        "body": (
            "Hello Cyberfield Support,\n\nURGENT — production halted. Please quote ASAP:\n"
            "- 2 × Centrifugal Process Pump C2 (NW-PMP-C2)\n"
            "- 4 × Mechanical Seal Rebuild Kit (NW-SEAL-KIT)\n\n"
            "Need delivery to Riverbend Plants, Cleveland OH within 3 weeks.\n\nJordan Blake\nPurchasing"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=1),
    },
    {
        "message_id": "gmail-mock-005-idler-rfq",
        "from_address": "maint@coastal-agg.example",
        "from_name": "Sam Ortiz",
        "subject": "RFQ: Conveyor idler rollers — 80 units",
        "body": (
            "Team,\n\nRequesting quotation for 80 × Conveyor Idler Roller 4-inch (NW-CNV-IDL).\n"
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
            "Hi again,\n\nCan you also quote 2 × 7.5 HP Variable Frequency Drive (NW-VFD-7)\n"
            "for our second packaging line?\n\nMarcus Chen\nSummit Packaging LLC"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=12),
    },
    {
        "message_id": "gmail-mock-007-escalation",
        "from_address": "vp.ops@midwest-steel.example",
        "from_name": "Dana Okonkwo",
        "subject": "Escalation: overdue quote on NW-MTR-3HP — CEO reviewing suppliers",
        "body": (
            "Cyberfield Support,\n\nThis is an escalation / final notice. We requested a quote two weeks ago for\n"
            "12 × NW-MTR-3HP motors (~$8,200). Our CEO is reviewing suppliers Friday.\n"
            "Please respond urgently or we will cancel the RFQ.\n\nDana Okonkwo\nVP Operations — Midwest Steel"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=4),
    },
    {
        "message_id": "gmail-mock-008-po-confirm",
        "from_address": "buyer@riverbend-plants.example",
        "from_name": "Jordan Blake",
        "subject": "PO-4412 released — please confirm order",
        "body": (
            "Hello,\n\nPurchase order PO-4412 is released for the pump package ($4,860).\n"
            "Please confirm order acknowledgment and shipment window to Cleveland OH.\n\nJordan Blake\nPurchasing"
        ),
        "received_at": _MOCK_NOW - timedelta(days=1),
    },
    {
        "message_id": "gmail-mock-009-shipping",
        "from_address": "recv@lakeside-mfg.example",
        "from_name": "Priya Nair",
        "subject": "Where is shipment for PO-3890? Need tracking / ETA",
        "body": (
            "Hi logistics,\n\nCan you share tracking and delivery status for PO-3890?\n"
            "Carrier was supposed to deliver last week. Lead time update appreciated.\n\nPriya Nair\nLakeside Manufacturing"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=6),
    },
    {
        "message_id": "gmail-mock-010-complaint",
        "from_address": "qa@summit-packaging.example",
        "from_name": "Alex Rivera",
        "subject": "Quality complaint — damaged seal kit, need RMA",
        "body": (
            "We received NW-SEAL-KIT lot that arrived damaged / defective.\n"
            "This is unacceptable for our line. Please open an RMA and advise replacement or refund.\n\nAlex Rivera\nQA — Summit Packaging"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=3),
    },
    {
        "message_id": "gmail-mock-011-meeting",
        "from_address": "proc@harbor-logistics.example",
        "from_name": "Elena Rossi",
        "subject": "Demo / discovery call next week?",
        "body": (
            "Good afternoon,\n\nWe would like to schedule a meeting / product demo for conveyor idlers and pumps.\n"
            "Available Tuesday 2pm or Thursday morning. Zoom preferred.\n\nElena Rossi\nHarbor Logistics"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=10),
    },
    {
        "message_id": "gmail-mock-012-invoice",
        "from_address": "ap@coastal-agg.example",
        "from_name": "Finance Desk",
        "subject": "Remittance advice — INV-2201 paid $3,240 via ACH",
        "body": (
            "Hello AR team,\n\nPlease find remittance for invoice INV-2201.\n"
            "Amount due paid: $3,240.00 USD via ACH today. PO-4100 referenced.\n\nAccounts Payable\nCoastal Aggregates"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=9),
    },
    {
        "message_id": "gmail-mock-013-catalog",
        "from_address": "eng@midwest-steel.example",
        "from_name": "Chris Patel",
        "subject": "Datasheet + COA request for NW-BRG-6205",
        "body": (
            "Please send the latest datasheet and certificate of analysis (COA) for Industrial Ball Bearing 6205-2RS.\n"
            "Also confirm current availability / in-stock quantity.\n\nChris Patel\nEngineering"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=14),
    },
    {
        "message_id": "gmail-mock-014-change-order",
        "from_address": "ops@summit-packaging.example",
        "from_name": "Marcus Chen",
        "subject": "Change order — amend quote Q-prior: reduce VFD qty to 2",
        "body": (
            "Please amend our previous quote / change order:\n"
            "Reduce 7.5 HP Variable Frequency Drive (NW-VFD-7) from 4 units to 2 units.\n"
            "Keep 3HP motors as quoted. Send revised quotation.\n\nMarcus Chen"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=7),
    },
    {
        "message_id": "gmail-mock-015-nda",
        "from_address": "legal@harbor-logistics.example",
        "from_name": "Morgan Lee",
        "subject": "NDA + partnership discussion — MSA draft attached",
        "body": (
            "Cyberfield Support team,\n\nWe would like to execute a non-disclosure agreement (NDA) and explore a "
            "distribution partnership. Please review our MSA draft and return redlines.\n\nMorgan Lee\nLegal / Partnerships"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=20),
    },
    {
        "message_id": "gmail-mock-016-vendor",
        "from_address": "vendors@lakeside-mfg.example",
        "from_name": "Supplier Portal",
        "subject": "Vendor onboarding — please complete compliance packet / W-9",
        "body": (
            "Hello,\n\nTo remain an approved vendor please complete supplier onboarding:\n"
            "- W-9 tax form\n- Insurance certificate\n- Compliance attestations\n"
            "Portal link will follow. Reply when ready.\n\nLakeside Vendor Management"
        ),
        "received_at": _MOCK_NOW - timedelta(hours=18),
    },
    # Noise — must be filtered by business_relevance
    {
        "message_id": "gmail-mock-noise-reddit",
        "from_address": "noreply@redditmail.com",
        "from_name": "Reddit",
        "subject": "r/industrialengineering — top posts this week",
        "body": "Your Reddit digest. Unsubscribe anytime. No action required.",
        "received_at": _MOCK_NOW - timedelta(hours=3),
        "expect_filtered": True,
    },
    {
        "message_id": "gmail-mock-noise-linkedin",
        "from_address": "messages-noreply@linkedin.com",
        "from_name": "LinkedIn",
        "subject": "You have 12 new notifications — weekly roundup",
        "body": "Sponsored marketing tips. Unsubscribe · Manage preferences.",
        "received_at": _MOCK_NOW - timedelta(hours=5),
        "expect_filtered": True,
    },
    {
        "message_id": "gmail-mock-noise-medium",
        "from_address": "noreply@medium.com",
        "from_name": "Medium",
        "subject": "Stories for you from Medium",
        "body": "Read this article. Top stories trending now. View in browser. Unsubscribe.",
        "received_at": _MOCK_NOW - timedelta(hours=2),
        "expect_filtered": True,
    },
    {
        "message_id": "gmail-mock-noise-substack",
        "from_address": "noreply@substack.com",
        "from_name": "Substack",
        "subject": "Your Substack digest: 5 new posts",
        "body": "Weekly newsletter digest from writers you follow. Manage preferences.",
        "received_at": _MOCK_NOW - timedelta(hours=4),
        "expect_filtered": True,
    },
    {
        "message_id": "gmail-mock-noise-github",
        "from_address": "notifications@github.com",
        "from_name": "GitHub",
        "subject": "[GitHub] You have new notifications",
        "body": "github notifications for your repositories. Pushed to main. Nothing commercial.",
        "received_at": _MOCK_NOW - timedelta(hours=1),
        "expect_filtered": True,
    },
    {
        "message_id": "gmail-mock-noise-newsletter",
        "from_address": "digest@industry-weekly.example",
        "from_name": "Industry Weekly",
        "subject": "This week in industrial supply — newsletter",
        "body": "Your daily digest / morning brief. Unsubscribe anytime.",
        "received_at": _MOCK_NOW - timedelta(hours=9),
        "expect_filtered": True,
    },
    {
        "message_id": "gmail-mock-noise-bse",
        "from_address": "alerts@bseindia.com",
        "from_name": "BSE ALERTS",
        "subject": "BSE ALERTS: Corporate Action — Scrip Code 500325",
        "body": (
            "BSE India market alert. Sensex update and equity corporate action notice. "
            "Stock exchange notification only. Unsubscribe / manage preferences."
        ),
        "received_at": _MOCK_NOW - timedelta(hours=1, minutes=20),
        "expect_filtered": True,
    },
    {
        "message_id": "gmail-mock-noise-unstop",
        "from_address": "team@unstop.com",
        "from_name": "Team Unstop",
        "subject": "Team Unstop — new hackathon & internship opportunities for you",
        "body": (
            "Hi! Apply now for this internship / hiring challenge on Unstop (formerly Dare2Compete). "
            "Career digest with job alerts. Promo — limited-time offer to register. Unsubscribe anytime."
        ),
        "received_at": _MOCK_NOW - timedelta(hours=2, minutes=10),
        "expect_filtered": True,
    },
]


def _auto_stage_enabled() -> bool:
    raw = os.environ.get("AUTO_STAGE_ON_SYNC", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


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
        detail = "Live Gmail API via refresh token (messages.list + get)"
    elif requested == "oauth" and not real_ready:
        mode = "mock"
        detail = (
            "GMAIL_MODE=oauth but GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / "
            "GOOGLE_REFRESH_TOKEN incomplete — using mock"
        )
    else:
        mode = "mock"
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
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gmail OAuth sync failed; falling back to mock")
            result = await _sync_mock(db)
            result["warning"] = f"OAuth sync failed ({exc}); used mock instead"
            result["mode"] = "mock"
    else:
        result = await _sync_mock(db)

    scored = recompute_all(db)
    result["attention_rescored"] = scored
    result["status"] = gmail_connection_status()
    if result.get("emails"):
        ids = [e.id for e in result["emails"]]
        result["emails"] = db.query(Email).filter(Email.id.in_(ids)).all() if ids else []
    return result


async def _stage_plan(db: Session, email: Email) -> bool:
    """Stage full ops plan for approval (email already classified)."""
    from app.models import Approval

    existing = (
        db.query(Approval)
        .filter(Approval.email_id == email.id, Approval.status == "pending")
        .first()
    )
    if existing:
        return False
    try:
        await run_ops_plan(db, email_id=email.id, auto_stage=True)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Auto-stage failed for email %s", email.id)
        return False


def _persist_new_email(
    db: Session,
    *,
    fields: dict[str, Any],
    catalog: dict[str, float],
    business_meta: dict[str, Any] | None = None,
) -> Email:
    email = Email(**fields)
    email.business_relevant = True
    email.business_meta = business_meta
    apply_attention(email, catalog=catalog)
    db.add(email)
    return email


def _try_import_fields(
    db: Session,
    *,
    fields: dict[str, Any],
    catalog: dict[str, float],
) -> tuple[Email | None, dict[str, Any] | None]:
    ok, classification = should_import_message(
        subject=fields.get("subject") or "",
        body=fields.get("body") or "",
        from_address=fields.get("from_address") or "",
        from_name=fields.get("from_name") or "",
        db=db,
    )
    meta = classification.as_meta()
    if not ok:
        return None, meta
    email = _persist_new_email(db, fields=fields, catalog=catalog, business_meta=meta)
    return email, meta


async def _sync_mock(db: Session) -> dict[str, Any]:
    created: list[Email] = []
    skipped = 0
    filtered = 0
    filtered_subjects: list[str] = []
    classified = 0
    plans_staged = 0
    catalog = catalog_prices(db)
    stage = _auto_stage_enabled()
    for row in MOCK_GMAIL_POOL:
        existing = db.query(Email).filter(Email.message_id == row["message_id"]).first()
        if existing:
            skipped += 1
            continue
        fields = {
            "message_id": row["message_id"],
            "from_address": row["from_address"],
            "from_name": row["from_name"],
            "to_address": "support@cyberfield.example",
            "subject": row["subject"],
            "body": row["body"],
            "received_at": row.get("received_at") or datetime.now(timezone.utc),
            "status": "unread",
        }
        email, meta = _try_import_fields(db, fields=fields, catalog=catalog)
        if email is None:
            filtered += 1
            filtered_subjects.append(row["subject"][:80])
            continue
        db.flush()
        created.append(email)

    db.commit()
    for email in created:
        await classify_email_on_ingest(db, email)
        classified += 1
    db.commit()

    if stage:
        for email in list(created):
            if await _stage_plan(db, email):
                plans_staged += 1

    meta_common = {
        "mode": "mock",
        "imported": len(created),
        "skipped": skipped,
        "filtered": filtered,
        "filtered_count": filtered,
        "filtered_subjects": filtered_subjects,
        "classified": classified,
        "plans_staged": plans_staged,
        "list_query": None,
    }
    db.add(
        ActivityLog(
            kind="gmail_sync",
            message=(
                f"Mock Gmail sync imported {len(created)} business message(s), "
                f"filtered {filtered} non-business"
                + (f", staged {plans_staged} action plan(s)" if plans_staged else "")
            ),
            meta={**meta_common, "message_ids": [e.message_id for e in created]},
        )
    )
    db.commit()
    for e in created:
        db.refresh(e)

    return {
        "mode": "mock",
        "imported": len(created),
        "skipped": skipped,
        "filtered": filtered,
        "filtered_count": filtered,
        "filtered_subjects": filtered_subjects,
        "classified": classified,
        "plans_staged": plans_staged,
        "emails": created,
        "status": gmail_connection_status(),
        "list_query": None,
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
    filtered = 0
    filtered_subjects: list[str] = []
    classified = 0
    plans_staged = 0
    catalog = catalog_prices(db)
    stage = _auto_stage_enabled()
    for msg in messages:
        mid = f"gmail-{msg['id']}"
        existing = db.query(Email).filter(Email.message_id == mid).first()
        if existing:
            skipped += 1
            continue
        parsed = _parse_gmail_message(msg)
        fields = {
            "message_id": mid,
            "from_address": parsed["from_address"],
            "from_name": parsed["from_name"],
            "to_address": parsed["to_address"],
            "subject": parsed["subject"],
            "body": parsed["body"],
            "received_at": parsed["received_at"],
            "status": "unread",
        }
        email, meta = _try_import_fields(db, fields=fields, catalog=catalog)
        if email is None:
            filtered += 1
            filtered_subjects.append((parsed["subject"] or "")[:80])
            continue
        created.append(email)

    db.commit()
    for email in created:
        await classify_email_on_ingest(db, email)
        classified += 1
    db.commit()
    if stage:
        for email in list(created):
            if await _stage_plan(db, email):
                plans_staged += 1

    db.add(
        ActivityLog(
            kind="gmail_sync",
            message=(
                f"Gmail OAuth sync imported {len(created)} business message(s), "
                f"filtered {filtered} non-business"
                + (f", staged {plans_staged} action plan(s)" if plans_staged else "")
            ),
            meta={
                "mode": "oauth",
                "imported": len(created),
                "skipped": skipped,
                "filtered": filtered,
                "filtered_count": filtered,
                "filtered_subjects": filtered_subjects,
                "classified": classified,
                "plans_staged": plans_staged,
                "list_query": GMAIL_LIST_QUERY,
            },
        )
    )
    db.commit()
    for e in created:
        db.refresh(e)

    return {
        "mode": "oauth",
        "imported": len(created),
        "skipped": skipped,
        "filtered": filtered,
        "filtered_count": filtered,
        "filtered_subjects": filtered_subjects,
        "classified": classified,
        "plans_staged": plans_staged,
        "emails": created,
        "status": gmail_connection_status(),
        "list_query": GMAIL_LIST_QUERY,
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
        return resp.json()["access_token"]


async def _list_gmail_messages(access_token: str, max_results: int = 25) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        listing = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params={"maxResults": max_results, "q": GMAIL_LIST_QUERY},
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
    if "<" in value and ">" in value:
        name = value.split("<", 1)[0].strip().strip('"')
        addr = value.split("<", 1)[1].split(">", 1)[0].strip()
        return name, addr
    return "", value.strip()


def _parse_gmail_message(msg: dict[str, Any]) -> dict[str, Any]:
    payload = msg.get("payload") or {}
    headers = _header_map(payload)
    from_name, from_address = _parse_from(headers.get("from", "unknown@example.com"))
    to_raw = headers.get("to", "support@cyberfield.example")
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
        "to_address": to_address or "support@cyberfield.example",
        "subject": subject,
        "body": body,
        "received_at": received_at,
    }


async def ingest_external_email(
    db: Session,
    *,
    from_address: str,
    subject: str,
    body: str,
    from_name: str = "",
    to_address: str = "support@cyberfield.example",
    message_id: str | None = None,
    source: str = "n8n",
) -> Email | dict[str, Any]:
    mid = message_id or f"{source}-{uuid4().hex[:16]}"
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
    fields = {
        "message_id": mid,
        "from_address": from_address,
        "from_name": from_name or from_address.split("@")[0],
        "to_address": to_address,
        "subject": subject,
        "body": body,
        "received_at": datetime.now(timezone.utc),
        "status": "unread",
    }
    email, meta = _try_import_fields(db, fields=fields, catalog=catalog)
    if email is None:
        db.add(
            ActivityLog(
                kind="webhook_filtered",
                message=f"Filtered non-business ingest via {source}: {subject[:80]}",
                meta={"source": source, "from": from_address, "message_id": mid, "business": meta},
            )
        )
        db.commit()
        return {
            "filtered": True,
            "message_id": mid,
            "status": "filtered",
            "filter_reasons": (meta or {}).get("reasons") or [],
            "business_meta": meta,
        }

    db.flush()
    await classify_email_on_ingest(db, email)
    db.add(
        ActivityLog(
            kind="webhook_ingest",
            message=f"Ingested email via {source}: {subject[:80]}",
            meta={
                "source": source,
                "from": from_address,
                "message_id": mid,
                "intent": email.intent,
                "attention_score": email.attention_score,
                "attention_label": email.attention_label,
                "business": meta,
            },
        )
    )
    db.commit()
    db.refresh(email)
    return email
