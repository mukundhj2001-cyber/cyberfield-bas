"""Business-relevance classifier for inbox ingest.

Heuristics work offline (mock LLM / no keys). Optional LLM refinement is used
only when a real provider is already configured and BUSINESS_FILTER_USE_LLM=1
— borderline messages only; never required for demos.

Prefer *not* importing noise: require clear B2B/ops signals, and veto social /
newsletter / digest / marketing chrome aggressively.
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
    (re.compile(r"\b(P\.?O\.?\s*[-:#]?\s*\d+|purchase\s+order)\b", re.I), 24, "purchase order"),
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
    (re.compile(r"\b(meeting|schedule|calendly|discovery\s+call|book\s+a\s+(call|demo|time)|zoom)\b", re.I), 18, "meeting/demo"),
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
    (re.compile(r"\breddit\b", re.I), 34, "reddit"),
    (re.compile(r"\bnewsletter\b", re.I), 30, "newsletter"),
    (re.compile(r"\bunsubscribe\b", re.I), 24, "unsubscribe"),
    (re.compile(r"\b(linkedin|twitter|x\.com|facebook|instagram|tiktok|pinterest|snapchat)\b", re.I), 28, "social network"),
    (re.compile(r"\b(promo(tion)?|promotional|sale\s+ends|%?\s*off\b|flash\s+sale|limited[- ]time\s+offer)\b", re.I), 22, "promo"),
    (re.compile(r"\b(weekly\s+roundup|daily\s+digest|weekly\s+digest|this\s+week\s+in|morning\s+brief|evening\s+brief)\b", re.I), 28, "media digest"),
    (re.compile(r"\b(digest|roundup|round[- ]up)\b", re.I), 16, "digest/roundup"),
    (re.compile(r"\b(no[- ]?reply|noreply|donotreply|do[- ]?not[- ]?reply)\b", re.I), 14, "no-reply"),
    (re.compile(r"\b(marketing|advertisement|sponsored|ad\s+campaign)\b", re.I), 20, "marketing"),
    (re.compile(r"\b(you\s+have\s+\d+\s+new\s+(notifications?|likes?|followers?|comments?))\b", re.I), 30, "social notification"),
    (re.compile(r"\b(password\s+reset|verify\s+your\s+email|security\s+alert|sign[- ]?in\s+code)\b", re.I), 18, "account noise"),
    (re.compile(r"\b(view\s+in\s+browser|manage\s+preferences|update\s+your\s+preferences|email\s+preferences)\b", re.I), 16, "bulk mail chrome"),
    (re.compile(
        r"@redditmail\.com\b|@linkedin\.com\b|@facebookmail\.com\b|@x\.com\b|"
        r"@substack\.com\b|@medium\.com\b|@mail\.medium\.com\b|"
        r"@github\.com\b|@notifications\.github\.com\b|"
        r"@email\.beehiiv\.com\b|@convertkit\.com\b|@mailchimp\.com\b",
        re.I,
    ), 34, "social/bulk sender"),
    (re.compile(r"\b(industry[- ]?weekly|media\s+digest|news\s+roundup|top\s+stories|trending\s+(now|posts?))\b", re.I), 26, "news roundup"),
    (re.compile(r"\b(substack|beehiiv|ghost\.io|buttondown)\b", re.I), 28, "newsletter platform"),
    (re.compile(r"\bmedium\.com\b|\bfrom\s+medium\b|\bstories?\s+for\s+you\b", re.I), 28, "medium/articles"),
    (re.compile(r"(github\s+notifications?|\[GitHub\]|new\s+pull\s+request|pushed\s+to\s+main)", re.I), 26, "github notification"),
    (re.compile(r"\b(your\s+(daily|weekly|monthly)\s+(newsletter|digest|update|briefing))\b", re.I), 28, "periodic newsletter"),
    (re.compile(r"\b(read\s+(this\s+)?(article|post|story)|new\s+post\s+from|just\s+published)\b", re.I), 18, "article/post"),
    (re.compile(r"\b(list[- ]?unsubscribe|bulk\s+mail|mass\s+email)\b", re.I), 20, "bulk list"),
    (re.compile(r"\b(coupon|deal\s+of\s+the\s+day|shop\s+now|free\s+shipping\s+on\s+orders)\b", re.I), 22, "retail promo"),
    (re.compile(r"\b(r/[a-z0-9_]+)\b", re.I), 30, "subreddit"),
]

NOISE_SENDER_RE = re.compile(
    r"^(noreply|no-reply|donotreply|do-not-reply|newsletter|digest|news|marketing|promo|"
    r"notifications?|hello|hi|team|updates?|mailer|campaign|info)@",
    re.I,
)

# Domains that are almost never B2B ops unless RFQ/PO/invoice strong hits
HARD_NOISE_DOMAINS: set[str] = {
    "redditmail.com",
    "reddit.com",
    "linkedin.com",
    "facebookmail.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "instagram.com",
    "substack.com",
    "medium.com",
    "mail.medium.com",
    "github.com",
    "notifications.github.com",
    "email.beehiiv.com",
    "beehiiv.com",
    "convertkit.com",
    "mailchimp.com",
    "sendgrid.net",
    "amazonses.com",
    "pinterest.com",
    "tiktok.com",
}

# Require clearer B2B signal than before (was 12 / soft pos>0 path)
BUSINESS_THRESHOLD = 16
NOISE_OVERRIDE = 14  # negative score that vetoes weak positives unless RFQ-strong
MIN_NET_SCORE = 12

STRONG_LABELS = {
    "RFQ",
    "RFP",
    "purchase order",
    "pricing request",
    "invoice",
    "procurement",
    "demo request",
    "meeting/demo",
    "RMA/quality",
    "NDA/MSA/partnership",
    "change order",
    "vendor compliance",
    "payment/remittance",
    "datasheet/COA",
    "tracking/ETA",
}


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


def _is_hard_noise_domain(domain: str) -> bool:
    if not domain:
        return False
    if domain in HARD_NOISE_DOMAINS:
        return True
    return any(domain.endswith("." + d) for d in HARD_NOISE_DOMAINS)


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
        neg += 12
        reasons.append("-noreply-style sender")

    dom = _domain_of(addr)
    hard_noise = _is_hard_noise_domain(dom)
    if hard_noise:
        neg += 20
        reasons.append("-hard-noise domain")

    allowlisted = False
    domains = allowlist_domains if allowlist_domains is not None else parse_allowlist_domains()
    if dom and domains and (dom in domains or any(dom.endswith("." + d) for d in domains)):
        allowlisted = True
        pos += 30
        reasons.append("+allowlisted domain")

    crm_known = False
    if crm_emails and addr in {e.lower() for e in crm_emails}:
        crm_known = True
        pos += 25
        reasons.append("+known CRM contact")

    strong_hits = [r[1:] for r in reasons if r.startswith("+") and r[1:] in STRONG_LABELS]
    # "quote" alone is weaker — only counts as strong with another commercial signal
    has_quote = any(r == "+quote" for r in reasons)
    strong_business = bool(strong_hits) or (has_quote and pos >= 34 and neg < 10)

    score = float(pos - neg)
    if allowlisted or crm_known:
        is_business = True
    elif hard_noise and not strong_hits:
        # Reddit / Medium / Substack / GitHub / LinkedIn etc. — drop unless RFQ/PO/invoice
        is_business = False
    elif neg >= NOISE_OVERRIDE and not strong_hits:
        # Heavy social/marketing chrome without RFQ/PO/invoice → drop
        is_business = False
    elif strong_hits and (score >= 6 or pos >= BUSINESS_THRESHOLD):
        # Real RFQ/PO/complaint can survive unsubscribe footers or hard-noise domains
        is_business = True
    elif strong_business and score >= MIN_NET_SCORE:
        is_business = True
    elif pos >= BUSINESS_THRESHOLD and neg == 0 and score >= BUSINESS_THRESHOLD:
        # Clean B2B language, no noise chrome
        is_business = True
    elif pos >= BUSINESS_THRESHOLD and pos >= neg * 2 and score >= MIN_NET_SCORE:
        # Positives clearly dominate residual noise
        is_business = True
    else:
        # Neutral / personal / weak positives → drop from business inbox
        is_business = False
        if not reasons:
            reasons.append("-no business signals")
        elif not any(r.startswith("-") for r in reasons):
            reasons.append("-weak business signal")

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
