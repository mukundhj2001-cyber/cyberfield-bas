"""Inbox attention ranking — score messages so critical mail surfaces first.

Factors (weighted, capped):
  - urgency language / deadline dates
  - RFQ / quote intent
  - estimated deal value (catalog SKUs × qty, or $ amounts in text)
  - age + unread status
  - escalation keywords

Labels: Critical (>=70) · High (>=50) · Medium (>=30) · Low (<30)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import Email, Product

URGENCY_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\bASAP\b", re.I), 18, "ASAP"),
    (re.compile(r"\burgent(ly)?\b", re.I), 16, "urgent"),
    (re.compile(r"\bimmediately\b", re.I), 14, "immediately"),
    (re.compile(r"\btime[- ]sensitive\b", re.I), 14, "time-sensitive"),
    (re.compile(r"\bpriority\b", re.I), 8, "priority"),
    (re.compile(r"\bEOD\b|\bend of (the )?day\b", re.I), 12, "EOD"),
    (re.compile(r"\bEOW\b|\bend of (the )?week\b", re.I), 10, "EOW"),
    (re.compile(r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I), 10, "weekday deadline"),
    (re.compile(r"\bdeadline\b", re.I), 12, "deadline"),
    (re.compile(r"\bneed(ed)?\s+(by|within|before)\b", re.I), 10, "needed by"),
    (re.compile(r"\bwithin\s+\d+\s*(business\s+)?(day|week|hour)s?\b", re.I), 8, "delivery window"),
    (re.compile(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b"), 6, "date mentioned"),
]

QUOTE_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\bRFQ\b"), 22, "RFQ"),
    (re.compile(r"\bRFI\b"), 10, "RFI"),
    (re.compile(r"\bRFP\b"), 14, "RFP"),
    (re.compile(r"\bquot(e|ation|ing)\b", re.I), 18, "quote"),
    (re.compile(r"\bproposal\b", re.I), 12, "proposal"),
    (re.compile(r"\bplease\s+quote\b", re.I), 20, "please quote"),
    (re.compile(r"\brequest(ing)?\s+(a\s+)?(quot|pricing|price)\b", re.I), 18, "pricing request"),
    (re.compile(r"\bunits?\b|\bqty\b|\bquantity\b|\b×\b|\bx\s*\d+", re.I), 4, "quantities"),
]

ESCALATION_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\bescalat(e|ion)\b", re.I), 16, "escalation"),
    (re.compile(r"\bcomplaint\b|\bunsatisfied\b|\bunhappy\b", re.I), 14, "complaint"),
    (re.compile(r"\bcancel(lation)?\b", re.I), 12, "cancel"),
    (re.compile(r"\blegal\b|\battorney\b|\blawsuit\b", re.I), 18, "legal"),
    (re.compile(r"\bCEO\b|\bCFO\b|\bVP\b|\bdirector\b", re.I), 8, "executive"),
    (re.compile(r"\bfinal\s+notice\b|\blast\s+chance\b", re.I), 16, "final notice"),
    (re.compile(r"\bhold\s+(the\s+)?line\b|\bproduction\s+(down|stopped|halted)\b", re.I), 18, "production impact"),
    (re.compile(r"\bsla\b|\bbreach\b", re.I), 12, "SLA"),
]

DOLLAR_RE = re.compile(
    r"\$\s*([\d,]+(?:\.\d{1,2})?)\b|\b([\d,]+(?:\.\d{1,2})?)\s*(?:USD|dollars?)\b",
    re.I,
)
# Direct: "2 × NW-PMP-C2" or "NW-PMP-C2 x 2"
SKU_QTY_RE = re.compile(
    r"(?:(\d+)\s*[×x]\s*)?(NW-[A-Z0-9-]+)(?:\s*[×x]\s*(\d+))?",
    re.I,
)
# "80 × Conveyor Idler ... (NW-CNV-IDL)" — qty before name, SKU in parens
QTY_THEN_SKU_RE = re.compile(
    r"(\d+)\s*[×x]\s+[^\n]{0,80}?\((?:or\s+)?(NW-[A-Z0-9-]+)\)",
    re.I,
)
# "NW-BRG-6205 bearings (qty 50)" / "NW-BRG-6205, qty 50"
SKU_QTY_PAREN_RE = re.compile(
    r"(NW-[A-Z0-9-]+)[^\n]{0,40}?\(?\s*qty\.?\s*(\d+)\s*\)?",
    re.I,
)

LABEL_THRESHOLDS = (
    (70, "Critical"),
    (50, "High"),
    (30, "Medium"),
    (0, "Low"),
)


def label_for_score(score: float) -> str:
    for threshold, label in LABEL_THRESHOLDS:
        if score >= threshold:
            return label
    return "Low"


def _match_points(
    text: str, patterns: list[tuple[re.Pattern[str], int, str]], *, cap: int
) -> tuple[int, list[str]]:
    total = 0
    hits: list[str] = []
    for pattern, pts, name in patterns:
        if pattern.search(text):
            total += pts
            hits.append(name)
    return min(total, cap), hits


def _estimate_deal_value(text: str, catalog: dict[str, float]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    value = 0.0
    seen: set[str] = set()

    def _add(sku: str, qty: int) -> None:
        nonlocal value
        sku = sku.upper()
        key = f"{sku}:{qty}"
        if key in seen:
            return
        price = catalog.get(sku)
        if price is None:
            return
        seen.add(key)
        line = qty * price
        value += line
        reasons.append(f"{sku}×{qty}=${line:,.0f}")

    for m in QTY_THEN_SKU_RE.finditer(text):
        _add(m.group(2), int(m.group(1)))
    for m in SKU_QTY_PAREN_RE.finditer(text):
        _add(m.group(1), int(m.group(2)))
    for m in SKU_QTY_RE.finditer(text):
        qty_a, sku, qty_b = m.group(1), m.group(2), m.group(3)
        qty = int(qty_a or qty_b or 1)
        # Skip bare SKU-only hits when we already counted that SKU with an explicit qty
        if qty == 1 and any(s.startswith(sku.upper() + ":") for s in seen):
            continue
        _add(sku, qty)

    if value <= 0:
        for m in DOLLAR_RE.finditer(text):
            raw = m.group(1) or m.group(2) or "0"
            try:
                value = max(value, float(raw.replace(",", "")))
                reasons.append(f"${value:,.0f} mentioned")
            except ValueError:
                pass

    return value, reasons


def _value_points(value: float) -> tuple[int, str | None]:
    if value <= 0:
        return 0, None
    if value >= 20_000:
        return 25, f"deal≈${value:,.0f}"
    if value >= 8_000:
        return 20, f"deal≈${value:,.0f}"
    if value >= 3_000:
        return 15, f"deal≈${value:,.0f}"
    if value >= 1_000:
        return 10, f"deal≈${value:,.0f}"
    if value >= 200:
        return 6, f"deal≈${value:,.0f}"
    return 3, f"deal≈${value:,.0f}"


def _age_unread_points(
    *, status: str, received_at: Optional[datetime], now: datetime
) -> tuple[int, list[str]]:
    pts = 0
    reasons: list[str] = []
    unreadish = status in ("unread", "processing")
    if unreadish:
        pts += 8
        reasons.append("unread")
    elif status == "quoted":
        pts += 2
        reasons.append("already quoted")

    if received_at is not None:
        ts = received_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_hours = max(0.0, (now - ts).total_seconds() / 3600.0)
        if unreadish and age_hours >= 72:
            pts += 10
            reasons.append("stale unread >72h")
        elif unreadish and age_hours >= 24:
            pts += 6
            reasons.append("unread >24h")
        elif age_hours <= 6:
            pts += 5
            reasons.append("fresh <6h")
        elif age_hours <= 24:
            pts += 3
            reasons.append("today")
    return min(pts, 15), reasons


def score_message(
    *,
    subject: str,
    body: str,
    status: str = "unread",
    received_at: Optional[datetime] = None,
    catalog: Optional[dict[str, float]] = None,
    extracted: Optional[dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Return attention score, label, estimated value, and factor breakdown."""
    now = now or datetime.now(timezone.utc)
    catalog = catalog or {}
    text = f"{subject}\n{body}"

    urgency_pts, urgency_hits = _match_points(text, URGENCY_PATTERNS, cap=30)
    quote_pts, quote_hits = _match_points(text, QUOTE_PATTERNS, cap=25)
    esc_pts, esc_hits = _match_points(text, ESCALATION_PATTERNS, cap=20)

    est_value, value_hits = _estimate_deal_value(text, catalog)
    if extracted:
        # Prefer workflow extraction totals when present
        try:
            items = extracted.get("line_items") or []
            extracted_total = 0.0
            for item in items:
                sku = str(item.get("sku") or "").upper()
                qty = float(item.get("quantity") or 1)
                price = catalog.get(sku)
                if price is None and item.get("unit_price") is not None:
                    price = float(item["unit_price"])
                if price is not None:
                    extracted_total += qty * float(price)
            if extracted_total > est_value:
                est_value = extracted_total
                value_hits = [f"extracted≈${est_value:,.0f}"]
        except (TypeError, ValueError):
            pass

    value_pts, value_reason = _value_points(est_value)
    age_pts, age_hits = _age_unread_points(status=status, received_at=received_at, now=now)

    score = float(urgency_pts + quote_pts + value_pts + age_pts + esc_pts)
    # Soft cap keeps Critical meaningful without clipping High demos
    score = min(score, 100.0)
    label = label_for_score(score)

    reasons: list[str] = []
    reasons.extend(urgency_hits)
    reasons.extend(quote_hits)
    if value_reason:
        reasons.append(value_reason)
    reasons.extend(age_hits)
    reasons.extend(esc_hits)

    return {
        "attention_score": round(score, 1),
        "attention_label": label,
        "estimated_value": round(est_value, 2),
        "attention_meta": {
            "factors": {
                "urgency": urgency_pts,
                "quote_intent": quote_pts,
                "deal_value": value_pts,
                "age_unread": age_pts,
                "escalation": esc_pts,
            },
            "reasons": reasons[:12],
            "estimated_value": round(est_value, 2),
        },
    }


def catalog_prices(db: Session) -> dict[str, float]:
    return {p.sku.upper(): float(p.unit_price) for p in db.query(Product).all()}


def apply_attention(
    email: Email,
    *,
    catalog: Optional[dict[str, float]] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    result = score_message(
        subject=email.subject or "",
        body=email.body or "",
        status=email.status or "unread",
        received_at=email.received_at,
        catalog=catalog,
        extracted=email.extracted,
        now=now,
    )
    email.attention_score = result["attention_score"]
    email.attention_label = result["attention_label"]
    email.attention_meta = result["attention_meta"]
    return result


def recompute_all(db: Session) -> int:
    """Re-score every inbox message (e.g. after sync so age stays fresh)."""
    catalog = catalog_prices(db)
    now = datetime.now(timezone.utc)
    rows = db.query(Email).all()
    for email in rows:
        apply_attention(email, catalog=catalog, now=now)
    db.commit()
    return len(rows)


def recompute_one(db: Session, email: Email) -> dict[str, Any]:
    catalog = catalog_prices(db)
    result = apply_attention(email, catalog=catalog)
    db.commit()
    db.refresh(email)
    return result
