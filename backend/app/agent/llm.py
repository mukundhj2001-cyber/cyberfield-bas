"""LLM facade: real OpenAI/Anthropic when keyed, else deterministic mock."""

from __future__ import annotations

import json
import re
from typing import Any

from app.agent.intents import (
    CHANGE_ORDER,
    CONTRACT_PARTNERSHIP,
    ESCALATION,
    GENERAL_OPS,
    INVOICE_PAYMENT,
    MEETING_REQUEST,
    OTHER_BUSINESS,
    PRODUCT_INFO,
    PURCHASE_ORDER,
    RFQ_QUOTE,
    SHIPPING_STATUS,
    SUPPORT_COMPLAINT,
    VENDOR_ONBOARDING,
    normalize_intent,
)
from app.config import get_settings


def resolve_llm_mode() -> str:
    settings = get_settings()
    provider = (settings.llm_provider or "mock").lower().strip()
    if provider == "openai" and settings.openai_api_key:
        return "openai"
    if provider == "anthropic" and settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key and provider in {"mock", "auto", ""}:
        return "openai"
    if settings.anthropic_api_key and provider in {"mock", "auto", ""}:
        return "anthropic"
    return "mock"


async def classify_and_extract(email: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    mode = resolve_llm_mode()
    if mode == "openai":
        try:
            return await _openai_extract(email, catalog)
        except Exception as exc:  # noqa: BLE001
            result = mock_classify_and_extract(email, catalog)
            result["llm_fallback_reason"] = str(exc)
            result["llm_mode"] = "mock"
            return result
    if mode == "anthropic":
        try:
            return await _anthropic_extract(email, catalog)
        except Exception as exc:  # noqa: BLE001
            result = mock_classify_and_extract(email, catalog)
            result["llm_fallback_reason"] = str(exc)
            result["llm_mode"] = "mock"
            return result
    result = mock_classify_and_extract(email, catalog)
    result["llm_mode"] = "mock"
    return result


async def classify_intent_only(email: dict[str, Any]) -> dict[str, Any]:
    result = mock_classify_intent(email)
    result["llm_mode"] = "mock"
    return result


def mock_classify_intent(email: dict[str, Any]) -> dict[str, Any]:
    text = f"{email.get('subject', '')}\n{email.get('body', '')}".lower()
    subject = (email.get("subject") or "").lower()
    company = _guess_company(email)
    contact_name = email.get("from_name") or "Unknown Contact"

    intent, confidence = _score_intent(text, subject)
    amounts = _extract_amounts(text) if intent in {INVOICE_PAYMENT, PURCHASE_ORDER, CHANGE_ORDER} else []
    if intent == INVOICE_PAYMENT and not amounts:
        amounts = _extract_amounts(text)
    meeting_hint = _extract_meeting_hint(text) if intent == MEETING_REQUEST else None
    order_refs = _extract_order_refs(text)
    kb_refs = _kb_refs_for(intent)

    return {
        "intent": intent,
        "confidence": confidence,
        "contact_name": contact_name,
        "contact_email": email.get("from_address"),
        "company": company,
        "line_items": [],
        "amounts": amounts,
        "order_refs": order_refs,
        "meeting_hint": meeting_hint,
        "kb_refs": kb_refs,
        "notes": f"Intent classify from subject: {subject[:80]}",
        "llm_mode": "mock",
    }


def mock_classify_and_extract(email: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    base = mock_classify_intent(email)
    text = f"{email.get('subject', '')}\n{email.get('body', '')}".lower()
    subject = (email.get("subject") or "").lower()
    unique_items = _match_catalog_items(text, catalog)

    if unique_items and base["intent"] in {RFQ_QUOTE, CHANGE_ORDER, PRODUCT_INFO, OTHER_BUSINESS, GENERAL_OPS}:
        if re.search(r"\b(rfq|quote|quotation|pricing|price|how much|unit price|please quote|tender|rfp)\b", text):
            if base["intent"] != CHANGE_ORDER:
                base["intent"] = RFQ_QUOTE
            base["confidence"] = max(float(base["confidence"]), 0.9 if unique_items else 0.7)

    base["line_items"] = unique_items
    if not base.get("amounts") and unique_items:
        # estimated value hint for RFQ
        pass
    base["notes"] = f"Mock extract from subject: {subject[:80]}"
    return base


def _score_intent(text: str, subject: str) -> tuple[str, float]:
    scores: dict[str, float] = {i: 0.0 for i in (
        RFQ_QUOTE, PURCHASE_ORDER, INVOICE_PAYMENT, SHIPPING_STATUS, PRODUCT_INFO,
        SUPPORT_COMPLAINT, ESCALATION, MEETING_REQUEST, CONTRACT_PARTNERSHIP,
        CHANGE_ORDER, VENDOR_ONBOARDING, GENERAL_OPS, OTHER_BUSINESS,
    )}

    # RFQ / quote / tender / RFP
    if re.search(r"\b(rfq|request for quote|request for quotation|tender|rfp|request for proposal)\b", text):
        scores[RFQ_QUOTE] += 5.0
    if re.search(r"\b(please quote|unit price|pricing request|quotation|how much)\b", text):
        scores[RFQ_QUOTE] += 3.0
    if re.search(r"\b(quote|pricing)\b", text):
        scores[RFQ_QUOTE] += 1.2

    # Change order / amend
    if re.search(r"\b(change order|amend(ed|ment)? quote|revise(d)? quote|update (the )?quote|modify (po|order|quote))\b", text):
        scores[CHANGE_ORDER] += 5.0
    if re.search(r"\b(change qty|quantity change|add line|remove line item)\b", text):
        scores[CHANGE_ORDER] += 2.5

    # PO / reorder / order confirm
    if re.search(r"\b(purchase order|\bpo[- ]?\d+|po released|order confirmation|please confirm (our )?order|reorder)\b", text):
        scores[PURCHASE_ORDER] += 5.0
    if re.search(r"\b(placing (an )?order|firm order|blanket order)\b", text):
        scores[PURCHASE_ORDER] += 2.5

    # Invoice / payment
    if re.search(r"\b(invoice|remittance|accounts payable|payment due|billing|wire transfer|ach payment)\b", text):
        scores[INVOICE_PAYMENT] += 4.5
    if re.search(r"\b(net\s*30|amount due|paid in full|past due)\b", text):
        scores[INVOICE_PAYMENT] += 1.5

    # Shipping
    if re.search(r"\b(where is|tracking|shipment|shipping status|delivery status|eta|in transit|out for delivery|lead time)\b", text):
        scores[SHIPPING_STATUS] += 4.5
    if re.search(r"\b(shipped|deliver|tracking number|awb|carrier|freight)\b", text):
        scores[SHIPPING_STATUS] += 1.5

    # Product info / catalog / COA / datasheet
    if re.search(r"\b(datasheet|data sheet|coa\b|certificate of analysis|catalog|availability|in stock|spec sheet|cut sheet)\b", text):
        scores[PRODUCT_INFO] += 4.5
    if re.search(r"\b(distributor terms|product (info|information)|technical specs)\b", text):
        scores[PRODUCT_INFO] += 2.0

    # Support / complaint / RMA
    if re.search(r"\b(complaint|unhappy|unacceptable|frustrated|refund|defect|broken|wrong item|rma|return authorization|quality issue)\b", text):
        scores[SUPPORT_COMPLAINT] += 5.0
    if re.search(r"\b(not working|failed|damaged|support ticket|warranty claim)\b", text):
        scores[SUPPORT_COMPLAINT] += 2.0

    # Escalation / VIP / legal / cancel threat
    if re.search(r"\b(escalat|final notice|cancel (the )?(rfq|order|contract)|legal (action|team)|attorney|ceo reviewing|vip|executive escalation)\b", text):
        scores[ESCALATION] += 5.5
    if re.search(r"\b(or we will|last chance|production (halted|down)|critical supplier)\b", text):
        scores[ESCALATION] += 2.0

    # Meeting / demo
    if re.search(r"\b(meeting|schedule|calendly|book a (call|demo|time)|zoom|teams|demo request|discovery call)\b", text):
        scores[MEETING_REQUEST] += 4.0
    if re.search(r"\b(available (on|for)|let'?s meet|find time|sales call)\b", text):
        scores[MEETING_REQUEST] += 2.0

    # Contract / NDA / partnership
    if re.search(r"\b(nda|non[- ]disclosure|master (service|supply) agreement|\bmsa\b|partnership|joint venture|contract review)\b", text):
        scores[CONTRACT_PARTNERSHIP] += 5.0
    if re.search(r"\b(sign(ed)? (the )?agreement|legal review|terms and conditions)\b", text):
        scores[CONTRACT_PARTNERSHIP] += 1.5

    # Vendor onboarding / compliance
    if re.search(r"\b(vendor (onboarding|registration|portal)|supplier onboarding|w-?9|tax form|compliance (packet|docs)|insurance certificate|iso cert)\b", text):
        scores[VENDOR_ONBOARDING] += 5.0
    if re.search(r"\b(onboarding checklist|preferred supplier|approved vendor)\b", text):
        scores[VENDOR_ONBOARDING] += 2.0

    # General ops
    if re.search(r"\b(sla|ops update|process question|internal request)\b", text):
        scores[GENERAL_OPS] += 2.0

    # Subject boosts
    boosts = [
        (r"\b(rfq|quote|tender|rfp)\b", RFQ_QUOTE, 2.0),
        (r"\b(change order|amend)\b", CHANGE_ORDER, 2.5),
        (r"\b(purchase order|\bpo[- ]?\d+|reorder)\b", PURCHASE_ORDER, 2.5),
        (r"\b(invoice|remittance|payment)\b", INVOICE_PAYMENT, 2.0),
        (r"\b(shipping|shipment|tracking|delivery|eta)\b", SHIPPING_STATUS, 2.0),
        (r"\b(catalog|datasheet|coa|availability)\b", PRODUCT_INFO, 2.0),
        (r"\b(complaint|rma|quality|defect)\b", SUPPORT_COMPLAINT, 2.0),
        (r"\b(escalat|final notice|cancel|legal|vip)\b", ESCALATION, 2.5),
        (r"\b(meeting|schedule|demo|call)\b", MEETING_REQUEST, 2.0),
        (r"\b(nda|contract|partnership|msa)\b", CONTRACT_PARTNERSHIP, 2.5),
        (r"\b(onboarding|compliance|w-?9|vendor)\b", VENDOR_ONBOARDING, 2.0),
    ]
    for pat, intent, w in boosts:
        if re.search(pat, subject):
            scores[intent] += w


    # Resolve common overlaps (shipping vs PO, escalation vs RFQ)
    if scores[SHIPPING_STATUS] >= 3.5 and scores[PURCHASE_ORDER] > 0:
        scores[SHIPPING_STATUS] += 2.0
        scores[PURCHASE_ORDER] *= 0.5
    if scores[ESCALATION] >= 4.0:
        scores[ESCALATION] += 2.0
        scores[RFQ_QUOTE] *= 0.45
    if scores[MEETING_REQUEST] >= 3.5:
        scores[MEETING_REQUEST] += 1.5
    if scores[CONTRACT_PARTNERSHIP] >= 4.0:
        scores[CONTRACT_PARTNERSHIP] += 1.5

    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] < 1.5:
        return OTHER_BUSINESS, 0.55
    conf = min(0.96, 0.52 + best[1] * 0.07)
    return best[0], round(conf, 3)


def _kb_refs_for(intent: str) -> list[dict[str, str]]:
    catalog = {
        RFQ_QUOTE: [{"title": "Standard quote terms", "ref": "KB-QUOTE-TERMS"}],
        PRODUCT_INFO: [
            {"title": "Product catalog index", "ref": "KB-CATALOG"},
            {"title": "Datasheet library", "ref": "KB-DATASHEETS"},
            {"title": "COA request process", "ref": "KB-COA"},
        ],
        SHIPPING_STATUS: [
            {"title": "Lead-time matrix", "ref": "KB-LEADTIMES"},
            {"title": "Carrier tracking tips", "ref": "KB-TRACKING"},
        ],
        SUPPORT_COMPLAINT: [
            {"title": "RMA policy", "ref": "KB-RMA"},
            {"title": "Quality complaint playbook", "ref": "KB-QA"},
        ],
        ESCALATION: [{"title": "Escalation playbook", "ref": "KB-ESC"}],
        VENDOR_ONBOARDING: [
            {"title": "Vendor compliance packet", "ref": "KB-VENDOR"},
            {"title": "W-9 / insurance checklist", "ref": "KB-COMPLIANCE"},
        ],
        CONTRACT_PARTNERSHIP: [{"title": "NDA / MSA templates", "ref": "KB-LEGAL"}],
        INVOICE_PAYMENT: [{"title": "AR remittance guide", "ref": "KB-AR"}],
        PURCHASE_ORDER: [{"title": "Order acknowledgment SOP", "ref": "KB-OA"}],
        CHANGE_ORDER: [{"title": "Quote amendment SOP", "ref": "KB-CHANGE"}],
        MEETING_REQUEST: [{"title": "Demo scheduling guide", "ref": "KB-DEMO"}],
    }
    return catalog.get(intent, [])


def _match_catalog_items(text: str, catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    line_items: list[dict[str, Any]] = []
    for product in catalog:
        sku = product["sku"].lower()
        name = product["name"].lower()
        tokens = [t for t in re.split(r"[^a-z0-9]+", name) if len(t) > 3]
        matched = sku in text or any(tok in text for tok in tokens[:4])
        if not matched:
            for frag in (
                "6205", "bearing", "seal rebuild", "3hp", "induction motor",
                "vfd", "variable frequency", "idler", "centrifugal",
            ):
                if frag in text and frag in (sku + " " + name):
                    matched = True
                    break
        if not matched:
            continue
        qty = _extract_qty_near(text, sku, tokens)
        line_items.append(
            {
                "sku": product["sku"],
                "name": product["name"],
                "quantity": qty,
                "unit_price": product["unit_price"],
                "unit": product["unit"],
            }
        )
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in line_items:
        if item["sku"] in seen:
            continue
        seen.add(item["sku"])
        unique.append(item)
    return unique


def _extract_amounts(text: str) -> list[dict[str, Any]]:
    amounts: list[dict[str, Any]] = []
    for m in re.finditer(r"\$\s*([\d,]+(?:\.\d{1,2})?)", text):
        raw = m.group(1).replace(",", "")
        try:
            amounts.append({"amount": float(raw), "currency": "USD", "raw": m.group(0)})
        except ValueError:
            continue
    for m in re.finditer(r"\b(usd|inr|eur)\s*([\d,]+(?:\.\d{1,2})?)", text, re.I):
        raw = m.group(2).replace(",", "")
        try:
            amounts.append({"amount": float(raw), "currency": m.group(1).upper(), "raw": m.group(0)})
        except ValueError:
            continue
    return amounts[:8]


def _extract_order_refs(text: str) -> list[str]:
    refs = re.findall(r"\b(?:PO|SO|INV|ORD|RMA|Q)[- ]?\d{3,8}\b", text, re.I)
    return list(dict.fromkeys(r.upper().replace(" ", "-") for r in refs))[:8]


def _extract_meeting_hint(text: str) -> str | None:
    m = re.search(
        r"\b((mon|tue|wed|thu|fri|sat|sun)[a-z]*\b.{0,40}\d{1,2}(:\d{2})?\s*(am|pm)?)",
        text,
        re.I,
    )
    if m:
        return m.group(1).strip()[:120]
    m = re.search(r"\b(next week|this week|tomorrow|asap)\b", text, re.I)
    if m:
        return m.group(1)
    return None


def _extract_qty_near(text: str, sku: str, tokens: list[str]) -> int:
    patterns = [
        rf"(\d+)\s*[×x]\s*.{{0,40}}{re.escape(sku)}",
        rf"{re.escape(sku)}.{{0,30}}(\d+)\s*(units?|ea|pcs|pieces)?",
        rf"(\d+)\s*(units?|ea|pcs|of)?\s*.{{0,40}}{re.escape(sku)}",
    ]
    for tok in tokens[:3]:
        patterns.append(rf"(\d+)\s*[×x]\s*.{{0,50}}{re.escape(tok)}")
        patterns.append(rf"(\d+)\s+(units?\s+of\s+)?[^\n]{{0,40}}{re.escape(tok)}")
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            for g in m.groups():
                if g and g.isdigit():
                    return max(1, int(g))
    tok_alt = "|".join(map(re.escape, tokens[:2])) if tokens else sku
    m = re.search(rf"[•\-\*]\s*(\d+)\s+units?.{{0,60}}({re.escape(sku)}|{tok_alt})", text)
    if m:
        return max(1, int(m.group(1)))
    return 1


def _guess_company(email: dict[str, Any]) -> str:
    body = email.get("body") or ""
    for line in body.splitlines():
        if re.search(r"^\s*(company|org(anization)?)\s*:", line, re.I):
            return line.split(":", 1)[1].strip()
        if "—" in line and len(line) < 80 and not line.lower().startswith("regards"):
            parts = [p.strip() for p in line.split("—")]
            tail = parts[-1].lower() if parts else ""
            if len(parts) >= 2 and (
                "manufacturing" in tail or "llc" in tail or "inc" in tail or "packaging" in tail
            ):
                return parts[-1]
    addr = email.get("from_address") or ""
    domain = addr.split("@")[-1] if "@" in addr else ""
    return domain.split(".")[0].replace("-", " ").title() if domain else "Unknown Co"


def _catalog_brief(catalog: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- {p['sku']}: {p['name']} @ ${p['unit_price']}/{p['unit']}" for p in catalog
    )


async def _openai_extract(email: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    import httpx

    settings = get_settings()
    prompt = _build_prompt(email, catalog)
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "Classify B2B ops email and extract fields as JSON."},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    data["llm_mode"] = "openai"
    return _normalize_extract(data, email)


async def _anthropic_extract(email: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    import httpx

    settings = get_settings()
    prompt = _build_prompt(email, catalog)
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        content = resp.json()["content"][0]["text"]
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    data = json.loads(content)
    data["llm_mode"] = "anthropic"
    return _normalize_extract(data, email)


def _build_prompt(email: dict[str, Any], catalog: list[dict[str, Any]]) -> str:
    from app.agent.intents import ALL_INTENTS

    intents = ", ".join(ALL_INTENTS)
    return (
        "Classify this inbound B2B email and extract actionable fields.\n"
        f"Return JSON with keys: intent ({intents}), confidence (0-1),\n"
        "contact_name, contact_email, company, line_items (array of {sku,name,quantity,unit_price,unit}),\n"
        "amounts (array of {amount,currency,raw}), order_refs (string array), meeting_hint, notes.\n"
        "Only use SKUs from the catalog for line_items. If quantity missing, use 1.\n\n"
        f"CATALOG:\n{_catalog_brief(catalog)}\n\n"
        f"FROM: {email.get('from_name')} <{email.get('from_address')}>\n"
        f"SUBJECT: {email.get('subject')}\n"
        f"BODY:\n{email.get('body')}\n"
    )


def _normalize_extract(data: dict[str, Any], email: dict[str, Any]) -> dict[str, Any]:
    intent = normalize_intent(data.get("intent"))
    return {
        "intent": intent,
        "confidence": float(data.get("confidence") or 0.5),
        "contact_name": data.get("contact_name") or email.get("from_name") or "Unknown",
        "contact_email": data.get("contact_email") or email.get("from_address"),
        "company": data.get("company") or _guess_company(email),
        "line_items": data.get("line_items") or [],
        "amounts": data.get("amounts") or [],
        "order_refs": data.get("order_refs") or [],
        "meeting_hint": data.get("meeting_hint"),
        "kb_refs": data.get("kb_refs") or _kb_refs_for(intent),
        "notes": data.get("notes") or "",
        "llm_mode": data.get("llm_mode") or "unknown",
    }
