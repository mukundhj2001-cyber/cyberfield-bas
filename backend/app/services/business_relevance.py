"""Business-relevance classifier for inbox ingest.

Heuristics work offline (mock LLM / no keys). Optional LLM refinement is used
only when a real provider is already configured and BUSINESS_FILTER_USE_LLM=1
— borderline messages only; never required for demos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import get_settings

# --- Positive: B2B / ops language that needs attention ---
POSITIVE_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\bRFQ\b"), 28, "RFQ"),
    (re.compile(r"\bRFP\b"), 18, "RFP"),
    (re.compile(r"\bRFI\b"), 12, "RFI"),
    (re.compile(r"\bquot(e|ation|ing)\b", re.I), 22, "quote"),
    (re.compile(r"\binvoice\b", re.I), 18, "invoice"),
    (re.compile(r"\b(P\.?O\.?|purchase\s+order)\b", re.I), 24, "purchase order"),
    (re.compile(r"\bprocurement\b", re.I), 18, "procurement"),
    (re.compile(r"\b(suppliers?|vendors?)\b", re.I), 12, "supplier/vendor"),
    (re.compile(r"\bcustomers?\b", re.I), 8, "customer"),
    (re.compile(r"\b(work|sales|purchase)\s+orders?\b|\border\s+(#:|no\.?|number|qty|quantity|confirmation)\b", re.I), 10, "order"),
    (re.compile(r"\b(shipment|shipping|ship[- ]?to|delivery)\b", re.I), 10, "shipment/delivery"),
    (re.compile(r"\bSLA\b"), 14, "SLA"),
    (re.compile(r"\b(service\s+)?contracts?\b(?!\s+notes)", re.I), 12, "contract"),
    (re.compile(r"\bdemo\s+request\b|\brequest(ing)?\s+(a\s+)?demo\b", re.I), 16, "demo request"),
    (re.compile(r"\b(lead\s+time|net[- ]?\d+|unit\s+pric)", re.I), 10, "B2B commercial terms"),
    (re.compile(r"\b(distributor|wholesale|SKU|part\s+number|NW-[A-Z0-9-]+)\b", re.I), 10, "catalog/SKU"),
    (re.compile(r"\bescalat(e|ion)\b", re.I), 14, "escalation"),
    (re.compile(r"\bplease\s+quote\b|\brequest(ing)?\s+(a\s+)?(quot|pricing|price)\b", re.I), 24, "pricing request"),
    (re.compile(r"\b(line\s+items?|bill\s+of\s+materials|BOM)\b", re.I), 10, "line items/BOM"),
    (re.compile(r"\b(ops|operations|purchasing|sourcing)\b", re.I), 8, "ops/purchasing"),
    (re.compile(r"\b(meeting|schedule|calendly|discovery\s+call|book\s+a\s+(call|demo|time)|zoom)\b", re.I), 14, "meeting/demo"),
    (re.compile(r"\b(NDA|non[- ]disclosure|master\s+(service|supply)\s+agreement|\bMSA\b|partnership)\b", re.I), 16, "NDA/MSA/partnership"),
    (re.compile(r"\b(RMA|return\s+authorization|quality\s+(issue|complaint)|defective|warranty)\b", re.I), 16, "RMA/quality"),
    (re.compile(r"\b(tracking|ETA|in\s+transit|lead\s+time)\b", re.I), 12, "tracking/ETA"),
    (re.compile(r"\b(datasheet|data\s+sheet|COA|certificate\s+of\s+analysis|availability)\b", re.I), 14, "datasheet/COA"),
    (re.compile(r"\b(vendor\s+onboarding|supplier\s+onboarding|W-?9|compliance\s+(packet|docs)|insurance\s+certificate)\b", re.I), 16, "vendor compliance"),
    (re.compile(r"\b(remittance|accounts\s+payable|ACH|wire\s+transfer)\b", re.I), 14, "payment/remittance"),
    (re.compile(r"\b(change\s+order|amend(ed|ment)?\s+quote)\b", re.I), 16, "change order"),
]

# --- Negative: social / marketing / digests / personal clutter ---
NEGATIVE_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\breddit\b", re.I), 30, "reddit"),
    (re.compile(r"\bnewsletter\b", re.I), 28, "newsletter"),
    (re.compile(r"\bunsubscribe\b", re.I), 22, "unsubscribe"),
    (re.compile(r"\b(linkedin|twitter|x\.com|facebook|instagram|tiktok)\b", re.I), 24, "social network"),
    (re.compile(r"\b(promo(tion)?|promotional|sale\s+ends|%?\s*off\b|flash\s+sale)\b", re.I), 20, "promo"),
    (re.compile(r"\b(weekly\s+roundup|daily\s+digest|weekly\s+digest|this\s+week\s+in)\b", re.I), 26, "media digest"),
    (re.compile(r"\b(no[- ]?reply|noreply|donotreply|do[- ]?not[- ]?reply)\b", re.I), 12, "no-reply"),
    (re.compile(r"\b(marketing|advertisement|sponsored)\b", re.I), 18, "marketing"),
    (re.compile(r"\b(you\s+have\s+\d+\s+new\s+(notifications?|likes?|followers?))\b", re.I), 28, "social notification"),
    (re.compile(r"\b(password\s+reset|verify\s+your\s+email|security\s+alert)\b", re.I), 16, "account noise"),
    (re.compile(r"\b(view\s+in\s+browser|manage\s+preferences)\b", re.I), 14, "bulk mail chrome"),
    (re.compile(r"@redditmail\.com\b|@linkedin\.com\b|@facebookmail\.com\b|@x\.com\b", re.I), 30, "social sender"),
    (re.compile(r"\b(industry[- ]?weekly|media\s+digest|news\s+roundup)\b", re.I), 24, "news roundup"),
]

NOISE_SENDER_RE = re.compile(
    r"^(noreply|no-reply|donotreply|do-not-reply|newsletter|digest|news|marketing|promo|notifications?)@",
    re.I,
)

BUSINESS_THRESHOLD = 12
NOISE_OVERRIDE = 18  # negative score that can veto weak positives unless RFQ-strong


@dataclass
class BusinessRelevanceResult:
    is_business: bool
    score: float
    positive_score: int = 0
    negative_score: int = 0
    reasons: list[str] = field(default_factory=list)
    method: str = "heuristic"
    allowlisted: bool = False
    crm_known: bool = False

    def as_meta(self) -> dict[str, Any]:
        return {
            "is_business": self.is_business,
            "score": self.score,
            "positive_score": self.positive_score,
            "negative_score": self.negative_score,
            "reasons": self.reasons[:12],
            "method": self.method,
            "allowlisted": self.allowlisted,
            "crm_known": self.crm_known,
        }


def _domain_of(address: str) -> str:
    addr = (address or "").strip().lower()
    if "@" not in addr:
        return ""
    return addr.rsplit("@", 1)[-1].strip()


def parse_allowlist_domains(raw: Optional[str] = None) -> set[str]:
    settings = get_settings()
    text = raw if raw is not None else (settings.business_email_domains or "")
    return {d.strip().lower().lstrip("@") for d in text.split(",") if d.strip()}


def classify_business_relevance(
    *,
    subject: str,
    body: str,
    from_address: str,
    from_name: str = "",
    crm_emails: Optional[set[str]] = None,
    allowlist_domains: Optional[set[str]] = None,
) -> BusinessRelevanceResult:
    """Heuristic business vs noise classification (offline-safe)."""
    text = f"{subject or ''}\n{body or ''}\n{from_name or ''}\n{from_address or ''}"
    pos = 0
    neg = 0
    reasons: list[str] = []

    for pattern, pts, name in POSITIVE_PATTERNS:
        if pattern.search(text):
            pos += pts
            reasons.append(f"+{name}")

    for pattern, pts, name in NEGATIVE_PATTERNS:
        if pattern.search(text):
            neg += pts
            reasons.append(f"-{name}")

    addr = (from_address or "").strip().lower()
    if NOISE_SENDER_RE.search(addr):
        # Soft penalty — can still be overridden by strong RFQ from noreply billing
        neg += 10
        reasons.append("-noreply-style sender")

    allowlisted = False
    domains = allowlist_domains if allowlist_domains is not None else parse_allowlist_domains()
    dom = _domain_of(addr)
    if dom and domains and (dom in domains or any(dom.endswith("." + d) for d in domains)):
        allowlisted = True
        pos += 30
        reasons.append("+allowlisted domain")

    crm_known = False
    if crm_emails and addr in {e.lower() for e in crm_emails}:
        crm_known = True
        pos += 25
        reasons.append("+known CRM contact")

    # Strong B2B intent labels (not weak hits like bare "quote" in marketing)
    strong_labels = {"RFQ", "RFP", "purchase order", "pricing request", "invoice", "procurement", "demo request"}
    strong_hits = [r[1:] for r in reasons if r.startswith("+") and r[1:] in strong_labels]
    # "quote" alone is weaker — only counts as strong with another commercial signal
    has_quote = any(r == "+quote" for r in reasons)
    strong_business = bool(strong_hits) or (has_quote and pos >= 30 and neg < 10)

    score = float(pos - neg)
    if allowlisted or crm_known:
        is_business = True
    elif neg >= NOISE_OVERRIDE and not strong_hits:
        # Heavy social/marketing chrome without RFQ/PO/invoice → drop
        is_business = False
    elif strong_hits and score >= 8:
        # Real RFQ/PO can survive light unsubscribe footer chrome
        is_business = True
    elif strong_business and score > 0:
        is_business = True
    elif pos >= BUSINESS_THRESHOLD and pos > neg and score >= 8:
        is_business = True
    elif pos > 0 and neg == 0:
        is_business = True
    else:
        # Neutral / personal clutter → drop from business inbox
        is_business = False
        if not reasons:
            reasons.append("-no business signals")

    return BusinessRelevanceResult(
        is_business=is_business,
        score=round(score, 1),
        positive_score=pos,
        negative_score=neg,
        reasons=reasons,
        method="heuristic",
        allowlisted=allowlisted,
        crm_known=crm_known,
    )


def crm_email_set(db: Any) -> set[str]:
    """Collect known CRM contact emails (lazy import to avoid cycles)."""
    try:
        from app.models import Contact

        return {c.email.lower() for c in db.query(Contact).all() if c.email}
    except Exception:  # noqa: BLE001
        return set()


def should_import_message(
    *,
    subject: str,
    body: str,
    from_address: str,
    from_name: str = "",
    db: Any = None,
) -> tuple[bool, BusinessRelevanceResult]:
    """Return (import?, classification). Honors BUSINESS_FILTER_ENABLED."""
    settings = get_settings()
    if not settings.business_filter_enabled:
        return True, BusinessRelevanceResult(
            is_business=True,
            score=0,
            reasons=["filter disabled"],
            method="disabled",
        )
    crm = crm_email_set(db) if db is not None else set()
    result = classify_business_relevance(
        subject=subject,
        body=body,
        from_address=from_address,
        from_name=from_name,
        crm_emails=crm,
    )
    return result.is_business, result


def reclassify_existing_emails(db: Any) -> dict[str, int]:
    """Re-run classifier on stored rows; mark non-business (keep row, hide from inbox).

    Prefer-not-import is the sync path; this cleans legacy seed/demo DBs that
    already persisted newsletters before the filter existed.
    """
    from app.models import Email

    settings = get_settings()
    if not settings.business_filter_enabled:
        return {"scanned": 0, "marked_non_business": 0, "marked_business": 0}

    crm = crm_email_set(db)
    scanned = 0
    marked_non = 0
    marked_biz = 0
    for email in db.query(Email).all():
        scanned += 1
        verdict = classify_business_relevance(
            subject=email.subject or "",
            body=email.body or "",
            from_address=email.from_address or "",
            from_name=email.from_name or "",
            crm_emails=crm,
        )
        email.business_meta = verdict.as_meta()
        was = bool(email.business_relevant) if email.business_relevant is not None else True
        email.business_relevant = verdict.is_business
        if verdict.is_business:
            marked_biz += 1
        else:
            marked_non += 1
            # Soft-hide: ignored status keeps attention UI clean for legacy noise
            if was and (email.status or "") == "unread":
                email.status = "ignored"
    db.commit()
    return {
        "scanned": scanned,
        "marked_non_business": marked_non,
        "marked_business": marked_biz,
    }
