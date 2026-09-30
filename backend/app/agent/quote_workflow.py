"""quote_from_email — clean state-machine workflow (LangGraph-compatible shape).

Stages:
  1. load_email
  2. classify_extract
  3. price_lookup
  4. draft_quote_and_email
  5. create_approval (human-in-the-loop gate)

On approve (separate API):
  log_send → upsert_crm → assign_task
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agent.llm import classify_and_extract, resolve_llm_mode
from app.config import get_settings
from app.models import ActivityLog, Approval, Contact, Deal, Email, Product, Task
from app.services.attention import recompute_one


class QuoteWorkflowError(Exception):
    pass


async def run_quote_from_email(
    db: Session,
    *,
    email_id: Optional[int] = None,
    message_id: Optional[str] = None,
) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    settings = get_settings()

    # --- 1. load_email ---
    email = _load_email(db, email_id=email_id, message_id=message_id)
    email.status = "processing"
    db.commit()
    trace.append({"step": "load_email", "email_id": email.id, "subject": email.subject})

    catalog = [
        {
            "sku": p.sku,
            "name": p.name,
            "unit_price": p.unit_price,
            "unit": p.unit,
            "in_stock": p.in_stock,
        }
        for p in db.query(Product).all()
    ]

    # --- 2. classify_extract ---
    extracted = await classify_and_extract(
        {
            "from_address": email.from_address,
            "from_name": email.from_name,
            "subject": email.subject,
            "body": email.body,
        },
        catalog,
    )
    email.intent = extracted.get("intent")
    email.extracted = extracted
    db.commit()
    # Refresh attention using extracted line items / deal value
    attention = recompute_one(db, email)
    trace.append(
        {
            "step": "classify_extract",
            "intent": extracted.get("intent"),
            "confidence": extracted.get("confidence"),
            "llm_mode": extracted.get("llm_mode"),
            "line_item_count": len(extracted.get("line_items") or []),
            "attention_score": attention.get("attention_score"),
            "attention_label": attention.get("attention_label"),
        }
    )

    if extracted.get("intent") != "quote_request":
        # Still create an approval with empty quote so ops can decide
        trace.append({"step": "price_lookup", "skipped": True, "reason": "not_quote_request"})

    # --- 3. price_lookup (re-assert prices from DB) ---
    priced_items = _price_lookup(db, extracted.get("line_items") or [])
    subtotal = round(sum(i["quantity"] * i["unit_price"] for i in priced_items), 2)
    trace.append({"step": "price_lookup", "items": len(priced_items), "subtotal": subtotal})

    # --- 4. draft_quote_and_email ---
    quote_ref = f"Q-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
    quote_draft = {
        "quote_ref": quote_ref,
        "company": extracted.get("company") or "Unknown",
        "contact_name": extracted.get("contact_name"),
        "contact_email": extracted.get("contact_email") or email.from_address,
        "currency": "USD",
        "line_items": priced_items,
        "subtotal": subtotal,
        "tax_rate": 0.0,
        "tax": 0.0,
        "total": subtotal,
        "validity_days": 30,
        "payment_terms": "Net 30",
        "lead_time": "7–10 business days",
        "notes": extracted.get("notes") or "",
        "seller": settings.company_name,
    }
    email_draft = _draft_email(quote_draft, original_subject=email.subject)
    trace.append({"step": "draft_quote_and_email", "quote_ref": quote_ref, "total": subtotal})

    # --- 5. create_approval ---
    approval = Approval(
        email_id=email.id,
        workflow="quote_from_email",
        status="pending",
        quote_draft=quote_draft,
        email_draft=email_draft,
        agent_trace=trace,
    )
    db.add(approval)
    email.status = "quoted"
    db.add(
        ActivityLog(
            kind="workflow",
            message=f"quote_from_email drafted {quote_ref} for {email.from_address}",
            meta={"email_id": email.id, "quote_ref": quote_ref},
        )
    )
    db.commit()
    db.refresh(approval)
    trace.append({"step": "create_approval", "approval_id": approval.id})
    approval.agent_trace = list(trace)
    db.commit()
    db.refresh(approval)

    return {
        "approval_id": approval.id,
        "email_id": email.id,
        "status": approval.status,
        "quote_draft": quote_draft,
        "email_draft": email_draft,
        "agent_trace": trace,
        "llm_mode": extracted.get("llm_mode") or resolve_llm_mode(),
    }


def approve_quote(
    db: Session,
    approval_id: int,
    *,
    reviewed_by: str = "Ops Manager",
    review_note: Optional[str] = None,
    quote_draft: Optional[dict[str, Any]] = None,
    email_draft: Optional[dict[str, Any]] = None,
) -> Approval:
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise QuoteWorkflowError(f"Approval {approval_id} not found")
    if approval.status != "pending":
        raise QuoteWorkflowError(f"Approval already {approval.status}")

    if quote_draft is not None:
        approval.quote_draft = quote_draft
    if email_draft is not None:
        approval.email_draft = email_draft

    quote = approval.quote_draft or {}
    draft = approval.email_draft or {}

    # --- log send (mock — no real SMTP) ---
    db.add(
        ActivityLog(
            kind="email_sent",
            message=f"Mock-sent quote {quote.get('quote_ref')} to {draft.get('to')}",
            meta={
                "approval_id": approval.id,
                "to": draft.get("to"),
                "subject": draft.get("subject"),
                "quote_ref": quote.get("quote_ref"),
            },
        )
    )

    # --- upsert CRM contact + deal ---
    contact = (
        db.query(Contact)
        .filter(Contact.email == (quote.get("contact_email") or "").lower())
        .first()
    )
    if not contact:
        contact = Contact(
            name=quote.get("contact_name") or "Unknown",
            email=(quote.get("contact_email") or f"unknown-{approval.id}@example.com").lower(),
            company=quote.get("company") or "",
        )
        db.add(contact)
        db.flush()
    else:
        if quote.get("company"):
            contact.company = quote["company"]
        if quote.get("contact_name"):
            contact.name = quote["contact_name"]

    deal = Deal(
        title=f"Quote {quote.get('quote_ref')} — {quote.get('company')}",
        contact_id=contact.id,
        amount=float(quote.get("total") or 0),
        currency=quote.get("currency") or "USD",
        stage="quote_sent",
        source="email",
        quote_ref=quote.get("quote_ref"),
        notes=f"Auto-created from approval #{approval.id}",
    )
    db.add(deal)
    db.flush()

    db.add(
        ActivityLog(
            kind="crm_update",
            message=f"CRM deal created for {quote.get('quote_ref')} (${quote.get('total')})",
            meta={"deal_id": deal.id, "contact_id": contact.id},
        )
    )

    # --- assign follow-up task ---
    task = Task(
        title=f"Follow up on {quote.get('quote_ref')}",
        description=(
            f"Call/email {quote.get('contact_name')} at {quote.get('company')} "
            f"regarding quote {quote.get('quote_ref')} (total ${quote.get('total')})."
        ),
        status="open",
        assignee="Sales Ops",
        priority="high",
        related_deal_id=deal.id,
        related_email_id=approval.email_id,
        due_at=datetime.now(timezone.utc) + timedelta(days=3),
    )
    db.add(task)
    db.flush()
    db.add(
        ActivityLog(
            kind="task_created",
            message=f"Task assigned: {task.title}",
            meta={"task_id": task.id, "assignee": task.assignee},
        )
    )

    approval.status = "approved"
    approval.reviewed_by = reviewed_by
    approval.review_note = review_note
    approval.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(approval)
    return approval


def reject_quote(
    db: Session,
    approval_id: int,
    *,
    reviewed_by: str = "Ops Manager",
    review_note: Optional[str] = None,
) -> Approval:
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise QuoteWorkflowError(f"Approval {approval_id} not found")
    if approval.status != "pending":
        raise QuoteWorkflowError(f"Approval already {approval.status}")

    approval.status = "rejected"
    approval.reviewed_by = reviewed_by
    approval.review_note = review_note
    approval.decided_at = datetime.now(timezone.utc)
    db.add(
        ActivityLog(
            kind="workflow",
            message=f"Approval #{approval.id} rejected by {reviewed_by}",
            meta={"approval_id": approval.id, "note": review_note},
        )
    )
    db.commit()
    db.refresh(approval)
    return approval


def _load_email(
    db: Session, *, email_id: Optional[int], message_id: Optional[str]
) -> Email:
    q = db.query(Email)
    if email_id is not None:
        email = q.filter(Email.id == email_id).first()
    elif message_id:
        email = q.filter(Email.message_id == message_id).first()
    else:
        # Default: highest-attention unread first (critical mail first)
        email = (
            q.filter(Email.status == "unread")
            .order_by(Email.attention_score.desc(), Email.id.asc())
            .first()
        )
    if not email:
        raise QuoteWorkflowError("No email found to process")
    return email


def _price_lookup(db: Session, line_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priced: list[dict[str, Any]] = []
    for item in line_items:
        product = db.query(Product).filter(Product.sku == item.get("sku")).first()
        if not product:
            continue
        qty = int(item.get("quantity") or 1)
        unit_price = float(product.unit_price)
        priced.append(
            {
                "sku": product.sku,
                "name": product.name,
                "quantity": qty,
                "unit_price": unit_price,
                "unit": product.unit,
                "line_total": round(qty * unit_price, 2),
                "in_stock": product.in_stock,
            }
        )
    return priced


def _draft_email(quote: dict[str, Any], *, original_subject: str) -> dict[str, Any]:
    settings = get_settings()
    lines = []
    for item in quote.get("line_items") or []:
        lines.append(
            f"  • {item['quantity']} × {item['name']} ({item['sku']}) "
            f"@ ${item['unit_price']:.2f}/{item['unit']} = ${item['line_total']:.2f}"
        )
    items_block = "\n".join(lines) if lines else "  (no matched catalog lines — please review)"
    body = (
        f"Dear {quote.get('contact_name')},\n\n"
        f"Thank you for your inquiry. Please find quotation {quote.get('quote_ref')} "
        f"from {settings.company_name} below.\n\n"
        f"Line items:\n{items_block}\n\n"
        f"Subtotal: ${float(quote.get('subtotal') or 0):,.2f} {quote.get('currency')}\n"
        f"Total:    ${float(quote.get('total') or 0):,.2f} {quote.get('currency')}\n\n"
        f"Payment terms: {quote.get('payment_terms')}\n"
        f"Lead time: {quote.get('lead_time')}\n"
        f"Validity: {quote.get('validity_days')} days\n\n"
        f"Please reply to confirm or request changes.\n\n"
        f"Best regards,\n"
        f"{settings.company_name} Sales\n"
        f"(Draft prepared by Cyberfield BAS — pending human approval)\n"
    )
    return {
        "to": quote.get("contact_email"),
        "cc": "",
        "subject": f"Re: {original_subject} — Quote {quote.get('quote_ref')}",
        "body": body,
    }
