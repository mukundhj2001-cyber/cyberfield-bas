"""LLM facade: real OpenAI/Anthropic when keyed, else deterministic mock."""

from __future__ import annotations

import json
import re
from typing import Any

from app.config import get_settings


def resolve_llm_mode() -> str:
    settings = get_settings()
    provider = (settings.llm_provider or "mock").lower().strip()
    if provider == "openai" and settings.openai_api_key:
        return "openai"
    if provider == "anthropic" and settings.anthropic_api_key:
        return "anthropic"
    # Auto-detect keys if provider left as mock but key present
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
        except Exception as exc:  # noqa: BLE001 — fall back for demo resilience
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


def mock_classify_and_extract(email: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic keyword extractor — works offline without API keys."""
    text = f"{email.get('subject', '')}\n{email.get('body', '')}".lower()
    subject = (email.get("subject") or "").lower()

    is_quote = bool(
        re.search(r"\b(rfq|quote|quotation|pricing|price|how much|unit price)\b", text)
        or re.search(r"\b(need|request).{0,40}\b(quote|quotation|pricing)\b", text)
    )

    line_items: list[dict[str, Any]] = []
    for product in catalog:
        sku = product["sku"].lower()
        name = product["name"].lower()
        tokens = [t for t in re.split(r"[^a-z0-9]+", name) if len(t) > 3]
        matched = sku in text or any(tok in text for tok in tokens[:4])
        # Stronger match on distinctive product fragments
        if not matched:
            for frag in ("6205", "bearing", "seal rebuild", "3hp", "induction motor", "vfd", "variable frequency", "idler", "centrifugal"):
                if frag in text and frag in (sku + " " + name):
                    matched = True
                    break
        if not matched:
            continue
        qty = _extract_qty_near(text, sku, name, tokens)
        line_items.append(
            {
                "sku": product["sku"],
                "name": product["name"],
                "quantity": qty,
                "unit_price": product["unit_price"],
                "unit": product["unit"],
            }
        )

    # Deduplicate by sku
    seen: set[str] = set()
    unique_items = []
    for item in line_items:
        if item["sku"] in seen:
            continue
        seen.add(item["sku"])
        unique_items.append(item)

    company = _guess_company(email)
    contact_name = email.get("from_name") or "Unknown Contact"

    if is_quote and unique_items:
        intent = "quote_request"
        confidence = 0.92
    elif is_quote:
        intent = "quote_request"
        confidence = 0.7
    elif "catalog" in text or "distributor" in text:
        intent = "catalog_inquiry"
        confidence = 0.85
    else:
        intent = "general"
        confidence = 0.55

    return {
        "intent": intent,
        "confidence": confidence,
        "contact_name": contact_name,
        "contact_email": email.get("from_address"),
        "company": company,
        "line_items": unique_items,
        "notes": f"Mock extract from subject: {subject[:80]}",
        "llm_mode": "mock",
    }


def _extract_qty_near(text: str, sku: str, name: str, tokens: list[str]) -> int:
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
    # bullet style "• 4 units of ..."
    m = re.search(rf"[•\-\*]\s*(\d+)\s+units?.{{0,60}}({re.escape(sku)}|{'|'.join(map(re.escape, tokens[:2]))})", text)
    if m:
        return max(1, int(m.group(1)))
    return 1


def _guess_company(email: dict[str, Any]) -> str:
    body = email.get("body") or ""
    for line in body.splitlines():
        if re.search(r"^\s*(company|org(anization)?)\s*:", line, re.I):
            return line.split(":", 1)[1].strip()
        if "—" in line and len(line) < 80 and not line.lower().startswith("regards"):
            # e.g. "Procurement — Lakeside Manufacturing"
            parts = [p.strip() for p in line.split("—")]
            tail = parts[-1].lower() if parts else ""
            if len(parts) >= 2 and ("manufacturing" in tail or "llc" in tail or "inc" in tail or "packaging" in tail):
                return parts[-1]
    addr = email.get("from_address") or ""
    domain = addr.split("@")[-1] if "@" in addr else ""
    slug = domain.split(".")[0].replace("-", " ").title() if domain else "Unknown Co"
    return slug


def _catalog_brief(catalog: list[dict[str, Any]]) -> str:
    return "\n".join(f"- {p['sku']}: {p['name']} @ ${p['unit_price']}/{p['unit']}" for p in catalog)


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
                    {"role": "system", "content": "Extract RFQ fields as JSON."},
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
    # Strip fences if present
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    data = json.loads(content)
    data["llm_mode"] = "anthropic"
    return _normalize_extract(data, email)


def _build_prompt(email: dict[str, Any], catalog: list[dict[str, Any]]) -> str:
    return (
        "Classify this inbound B2B email and extract quotation line items matched to the catalog.\n"
        "Return JSON with keys: intent (quote_request|catalog_inquiry|general), confidence (0-1),\n"
        "contact_name, contact_email, company, line_items (array of {sku,name,quantity,unit_price,unit}), notes.\n"
        "Only use SKUs from the catalog. If quantity missing, use 1.\n\n"
        f"CATALOG:\n{_catalog_brief(catalog)}\n\n"
        f"FROM: {email.get('from_name')} <{email.get('from_address')}>\n"
        f"SUBJECT: {email.get('subject')}\n"
        f"BODY:\n{email.get('body')}\n"
    )


def _normalize_extract(data: dict[str, Any], email: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent": data.get("intent") or "general",
        "confidence": float(data.get("confidence") or 0.5),
        "contact_name": data.get("contact_name") or email.get("from_name") or "Unknown",
        "contact_email": data.get("contact_email") or email.get("from_address"),
        "company": data.get("company") or _guess_company(email),
        "line_items": data.get("line_items") or [],
        "notes": data.get("notes") or "",
        "llm_mode": data.get("llm_mode") or "unknown",
    }
