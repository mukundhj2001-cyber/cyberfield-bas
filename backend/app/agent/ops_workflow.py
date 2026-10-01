"""Multi-intent ops workflow — classify → extract → draft → stage → human approval.

Automates everything UP TO the approval gate. On approve, applies staged plan:
outbound mock-send, CRM create/update, tickets/tasks. Selective apply supported
via apply_flags on the decision payload.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agent.intents import (
    CHANGE_ORDER,
    CONTRACT_PARTNERSHIP,
    ESCALATION,
    INVOICE_PAYMENT,
    INTENT_LABELS,
    MEETING_REQUEST,
    PRODUCT_INFO,
    PURCHASE_ORDER,
    RFQ_QUOTE,
    SHIPPING_STATUS,
    SUPPORT_COMPLAINT,
    VENDOR_ONBOARDING,
    WORKFLOW_BY_INTENT,
    normalize_intent,
    suggested_action_for,
)
from app.agent.llm import classify_and_extract, classify_intent_only, resolve_llm_mode
from app.config import get_settings
from app.models import ActivityLog, Approval, Contact, Deal, Email, Product, Task, Ticket
from app.services.attention import recompute_one


class OpsWorkflowError(Exception):
    pass


def _draft_footer(settings: Any) -> str:
    """Return the consistent human-approval note for generated replies."""
    ai_name = getattr(settings, "ai_name", "Cyberfield AI")
    brand_name = getattr(settings, "brand_name", "Cyberfield BAS")
    return f"(Draft prepared by {ai_name} via {brand_name} — pending human approval)"


# Keep QuoteWorkflowError alias for older imports
QuoteWorkflowError = OpsWorkflowError


async def classify_email_on_ingest(db: Session, email: Email) -> dict[str, Any]:
    """Lightweight classify on sync/ingest — store intent + suggested_action."""
    result = await classify_intent_only(
        {
            "from_address": email.from_address,
            "from_name": email.from_name,
            "subject": email.subject,
            "body": email.body,
        }
    )
    intent = normalize_intent(result.get("intent"))
    email.intent = intent
    email.extracted = {
        **(email.extracted or {}),
        "intent": intent,
        "confidence": result.get("confidence"),
        "order_refs": result.get("order_refs") or [],
        "amounts": result.get("amounts") or [],
        "meeting_hint": result.get("meeting_hint"),
        "kb_refs": result.get("kb_refs") or [],
        "llm_mode": result.get("llm_mode") or "mock",
        "ingest_classify": True,
    }
    suggested = suggested_action_for(
        intent,
        attention_label=email.attention_label or "Low",
        confidence=float(result.get("confidence") or 0.7),
    )
    email.suggested_action = suggested
    db.add(email)
    db.flush()
    return suggested


async def run_ops_plan(
    db: Session,
    *,
    email_id: Optional[int] = None,
    message_id: Optional[str] = None,
    auto_stage: bool = True,
) -> dict[str, Any]:
    """Full extract + draft + stage pending approval for any intent."""
    trace: list[dict[str, Any]] = []
    settings = get_settings()
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

    extracted = await classify_and_extract(
        {
            "from_address": email.from_address,
            "from_name": email.from_name,
            "subject": email.subject,
            "body": email.body,
        },
        catalog,
    )
    intent = normalize_intent(extracted.get("intent"))
    # Prefer prior ingest intent if extract is vague other_business but ingest was specific
    if intent == "other_business" and email.intent and email.intent != "other_business":
        intent = normalize_intent(email.intent)
        extracted["intent"] = intent

    email.intent = intent
    email.extracted = extracted
    attention = recompute_one(db, email)
    suggested = suggested_action_for(
        intent,
        attention_label=attention.get("attention_label") or email.attention_label or "Low",
        confidence=float(extracted.get("confidence") or 0.7),
    )
    email.suggested_action = suggested
    db.commit()
    trace.append(
        {
            "step": "classify_extract",
            "intent": intent,
            "confidence": extracted.get("confidence"),
            "llm_mode": extracted.get("llm_mode"),
            "attention_label": attention.get("attention_label"),
            "suggested": suggested.get("label"),
        }
    )

    plan = _build_action_plan(db, email, extracted, suggested, settings)
    trace.append({"step": "build_action_plan", "actions": plan["actions"], "title": plan["title"]})

    if not auto_stage:
        email.status = "unread"
        db.commit()
        return {
            "email_id": email.id,
            "intent": intent,
            "suggested_action": suggested,
            "action_plan": plan,
            "status": "planned",
            "llm_mode": extracted.get("llm_mode") or resolve_llm_mode(),
            "agent_trace": trace,
        }

    # Stage pending approval (human gate) — do NOT send / CRM write yet
    approval = Approval(
        email_id=email.id,
        workflow=plan["workflow"],
        action_type=intent,
        title=plan["title"],
        status="pending",
        quote_draft=plan.get("quote_draft") or {},
        email_draft=plan.get("email_draft") or {},
        action_plan=plan,
        agent_trace=trace,
        apply_defaults=plan.get("apply_defaults") or {},
    )
    db.add(approval)
    email.status = "action_staged"
    db.add(
        ActivityLog(
            kind="workflow",
            message=f"Staged {INTENT_LABELS.get(intent, intent)} plan for {email.from_address}",
            meta={"email_id": email.id, "intent": intent, "workflow": plan["workflow"]},
        )
    )
    db.commit()
    db.refresh(approval)
    trace.append({"step": "create_approval", "approval_id": approval.id, "status": "pending"})
    approval.agent_trace = list(trace)
    db.commit()
    db.refresh(approval)

    return {
        "approval_id": approval.id,
        "email_id": email.id,
        "status": approval.status,
        "intent": intent,
        "workflow": plan["workflow"],
        "title": plan["title"],
        "quote_draft": plan.get("quote_draft") or {},
        "email_draft": plan.get("email_draft") or {},
        "action_plan": plan,
        "suggested_action": suggested,
        "agent_trace": trace,
        "llm_mode": extracted.get("llm_mode") or resolve_llm_mode(),
    }


# Back-compat entry used by quote router / webhooks
async def run_quote_from_email(
    db: Session,
    *,
    email_id: Optional[int] = None,
    message_id: Optional[str] = None,
) -> dict[str, Any]:
    return await run_ops_plan(db, email_id=email_id, message_id=message_id, auto_stage=True)


def approve_plan(
    db: Session,
    approval_id: int,
    *,
    reviewed_by: str = "Ops Manager",
    review_note: Optional[str] = None,
    quote_draft: Optional[dict[str, Any]] = None,
    email_draft: Optional[dict[str, Any]] = None,
    apply_flags: Optional[dict[str, bool]] = None,
) -> Approval:
    """Apply staged plan after human approval. Selective via apply_flags."""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise OpsWorkflowError(f"Approval {approval_id} not found")
    if approval.status != "pending":
        raise OpsWorkflowError(f"Approval already {approval.status}")

    if quote_draft is not None:
        approval.quote_draft = quote_draft
    if email_draft is not None:
        approval.email_draft = email_draft

    plan = dict(approval.action_plan or {})
    defaults = dict(approval.apply_defaults or plan.get("apply_defaults") or {})
    flags = {**defaults, **(apply_flags or {})}

    quote = approval.quote_draft or {}
    draft = approval.email_draft or {}
    intent = normalize_intent(approval.action_type or plan.get("intent"))
    email = db.query(Email).filter(Email.id == approval.email_id).first()

    results: dict[str, Any] = {"applied": [], "skipped": []}

    # 1) Outbound send (mock)
    if flags.get("send_outbound", True) and draft.get("to"):
        db.add(
            ActivityLog(
                kind="email_sent",
                message=f"Mock-sent reply to {draft.get('to')} ({intent})",
                meta={
                    "approval_id": approval.id,
                    "to": draft.get("to"),
                    "subject": draft.get("subject"),
                    "intent": intent,
                },
            )
        )
        results["applied"].append("send_outbound")
    else:
        results["skipped"].append("send_outbound")

    contact = None
    deal = None

    # 2) CRM contact
    if flags.get("crm_contact", True) and plan.get("crm_contact_draft"):
        cdraft = plan["crm_contact_draft"]
        contact = (
            db.query(Contact)
            .filter(Contact.email == (cdraft.get("email") or "").lower())
            .first()
        )
        if not contact:
            contact = Contact(
                name=cdraft.get("name") or "Unknown",
                email=(cdraft.get("email") or f"unknown-{approval.id}@example.com").lower(),
                company=cdraft.get("company") or "",
                phone=cdraft.get("phone") or "",
            )
            db.add(contact)
            db.flush()
            results["applied"].append("crm_contact_create")
        else:
            if cdraft.get("company"):
                contact.company = cdraft["company"]
            if cdraft.get("name"):
                contact.name = cdraft["name"]
            results["applied"].append("crm_contact_update")
    else:
        results["skipped"].append("crm_contact")

    # 3) CRM deal
    if flags.get("crm_deal", True) and plan.get("crm_deal_draft"):
        ddraft = plan["crm_deal_draft"]
        if contact is None and ddraft.get("contact_email"):
            contact = (
                db.query(Contact)
                .filter(Contact.email == ddraft["contact_email"].lower())
                .first()
            )
        deal = Deal(
            title=ddraft.get("title") or f"{INTENT_LABELS.get(intent, intent)} — pending",
            contact_id=contact.id if contact else None,
            amount=float(ddraft.get("amount") or quote.get("total") or 0),
            currency=ddraft.get("currency") or quote.get("currency") or "USD",
            stage=ddraft.get("stage") or "qualified",
            source=ddraft.get("source") or "email",
            quote_ref=ddraft.get("quote_ref") or quote.get("quote_ref"),
            notes=ddraft.get("notes") or f"From approval #{approval.id} ({intent})",
        )
        db.add(deal)
        db.flush()
        db.add(
            ActivityLog(
                kind="crm_update",
                message=f"CRM deal staged→created: {deal.title} (${deal.amount})",
                meta={"deal_id": deal.id, "contact_id": contact.id if contact else None},
            )
        )
        results["applied"].append("crm_deal")
    elif flags.get("crm_deal", False):
        results["skipped"].append("crm_deal")
    else:
        results["skipped"].append("crm_deal")

    # 4) Ticket
    ticket = None
    if flags.get("create_ticket", True) and plan.get("ticket_draft"):
        td = plan["ticket_draft"]
        ticket = Ticket(
            title=td.get("title") or f"Ticket from email #{approval.email_id}",
            description=td.get("description") or "",
            status=td.get("status") or "open",
            priority=td.get("priority") or "medium",
            category=td.get("category") or intent,
            assignee=td.get("assignee") or "Support",
            related_email_id=approval.email_id,
            related_approval_id=approval.id,
            escalate=bool(td.get("escalate")),
            extracted=td.get("extracted") or {},
        )
        db.add(ticket)
        db.flush()
        db.add(
            ActivityLog(
                kind="ticket_created",
                message=f"Ticket #{ticket.id}: {ticket.title}",
                meta={"ticket_id": ticket.id, "escalate": ticket.escalate},
            )
        )
        results["applied"].append("create_ticket")
    else:
        results["skipped"].append("create_ticket")

    # 5) Tasks (may be multiple)
    if flags.get("create_tasks", True):
        for tdraft in plan.get("task_drafts") or []:
            task = Task(
                title=tdraft.get("title") or "Follow-up",
                description=tdraft.get("description") or "",
                status="open",
                assignee=tdraft.get("assignee") or "Ops",
                priority=tdraft.get("priority") or "medium",
                related_deal_id=deal.id if deal else None,
                related_email_id=approval.email_id,
                related_ticket_id=ticket.id if ticket else None,
                kind=tdraft.get("kind") or intent,
                due_at=_parse_due(tdraft.get("due_days"), default_days=3),
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
            results["applied"].append(f"task:{task.id}")
    else:
        results["skipped"].append("create_tasks")

    if email:
        email.status = "resolved"
    approval.status = "approved"
    approval.reviewed_by = reviewed_by
    approval.review_note = review_note
    approval.decided_at = datetime.now(timezone.utc)
    plan_out = dict(plan)
    plan_out["apply_results"] = results
    approval.action_plan = plan_out
    db.commit()
    db.refresh(approval)
    return approval


def approve_quote(
    db: Session,
    approval_id: int,
    *,
    reviewed_by: str = "Ops Manager",
    review_note: Optional[str] = None,
    quote_draft: Optional[dict[str, Any]] = None,
    email_draft: Optional[dict[str, Any]] = None,
    apply_flags: Optional[dict[str, bool]] = None,
) -> Approval:
    return approve_plan(
        db,
        approval_id,
        reviewed_by=reviewed_by,
        review_note=review_note,
        quote_draft=quote_draft,
        email_draft=email_draft,
        apply_flags=apply_flags,
    )


def reject_quote(
    db: Session,
    approval_id: int,
    *,
    reviewed_by: str = "Ops Manager",
    review_note: Optional[str] = None,
) -> Approval:
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise OpsWorkflowError(f"Approval {approval_id} not found")
    if approval.status != "pending":
        raise OpsWorkflowError(f"Approval already {approval.status}")

    approval.status = "rejected"
    approval.reviewed_by = reviewed_by
    approval.review_note = review_note
    approval.decided_at = datetime.now(timezone.utc)
    email = db.query(Email).filter(Email.id == approval.email_id).first()
    if email and email.status == "action_staged":
        email.status = "unread"
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


def _parse_due(due_days: Any, default_days: int = 3) -> datetime:
    try:
        days = int(due_days) if due_days is not None else default_days
    except (TypeError, ValueError):
        days = default_days
    return datetime.now(timezone.utc) + timedelta(days=max(0, days))


def _load_email(
    db: Session, *, email_id: Optional[int], message_id: Optional[str]
) -> Email:
    q = db.query(Email)
    if email_id is not None:
        email = q.filter(Email.id == email_id).first()
    elif message_id:
        email = q.filter(Email.message_id == message_id).first()
    else:
        email = (
            q.filter(Email.status.in_(["unread", "action_staged"]))
            .filter(Email.business_relevant.is_(True))
            .filter(Email.status != "ignored")
            .order_by(Email.attention_score.desc(), Email.id.asc())
            .first()
        )
    if not email:
        raise OpsWorkflowError("No email found to process")
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


def _build_action_plan(
    db: Session,
    email: Email,
    extracted: dict[str, Any],
    suggested: dict[str, Any],
    settings: Any,
) -> dict[str, Any]:
    intent = normalize_intent(extracted.get("intent") or email.intent)
    workflow = WORKFLOW_BY_INTENT.get(intent, "general_ops")
    company = extracted.get("company") or "Unknown"
    contact_name = extracted.get("contact_name") or email.from_name or "Contact"
    contact_email = extracted.get("contact_email") or email.from_address
    attention = email.attention_label or "Low"
    critical = attention.lower() == "critical" or intent == ESCALATION
    order_refs = extracted.get("order_refs") or []
    amounts = extracted.get("amounts") or []
    kb_refs = extracted.get("kb_refs") or []
    meeting_hint = extracted.get("meeting_hint")

    quote_draft: dict[str, Any] = {}
    email_draft: dict[str, Any] = {}
    crm_contact = {
        "name": contact_name,
        "email": contact_email,
        "company": company,
        "phone": "",
    }
    crm_deal: dict[str, Any] | None = None
    ticket_draft: dict[str, Any] | None = None
    task_drafts: list[dict[str, Any]] = []
    apply_defaults = {
        "send_outbound": True,
        "crm_contact": True,
        "crm_deal": False,
        "create_ticket": False,
        "create_tasks": True,
    }

    if intent in {RFQ_QUOTE, CHANGE_ORDER}:
        priced = _price_lookup(db, extracted.get("line_items") or [])
        subtotal = round(sum(i["quantity"] * i["unit_price"] for i in priced), 2)
        quote_ref = f"Q-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
        if intent == CHANGE_ORDER:
            quote_ref = f"CQ-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:5].upper()}"
        quote_draft = {
            "quote_ref": quote_ref,
            "company": company,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "currency": "USD",
            "line_items": priced,
            "subtotal": subtotal,
            "tax_rate": 0.0,
            "tax": 0.0,
            "total": subtotal,
            "validity_days": 30,
            "payment_terms": "Net 30",
            "lead_time": "7–10 business days",
            "notes": extracted.get("notes") or "",
            "seller": settings.company_name,
            "amendment": intent == CHANGE_ORDER,
        }
        email_draft = _draft_quote_email(quote_draft, original_subject=email.subject, settings=settings)
        crm_deal = {
            "title": f"{'Amended quote' if intent == CHANGE_ORDER else 'Quote'} {quote_ref} — {company}",
            "amount": subtotal,
            "currency": "USD",
            "stage": "quote_sent",
            "source": "email",
            "quote_ref": quote_ref,
            "contact_email": contact_email,
            "notes": f"Auto-staged from {intent}",
        }
        task_drafts.append(
            {
                "title": f"Follow up on {quote_ref}",
                "description": f"Follow up with {contact_name} at {company} on {quote_ref} (${subtotal}).",
                "assignee": "Sales Ops",
                "priority": "high" if critical else "medium",
                "due_days": 2 if critical else 3,
                "kind": intent,
            }
        )
        apply_defaults["crm_deal"] = True

    elif intent == PURCHASE_ORDER:
        email_draft = {
            "to": contact_email,
            "cc": "",
            "subject": f"Re: {email.subject} — Order acknowledgment",
            "body": (
                f"Dear {contact_name},\n\n"
                f"Thank you for your purchase order"
                f"{(' ' + ', '.join(order_refs)) if order_refs else ''}. "
                f"We have received it and are preparing fulfillment.\n\n"
                f"Our ops team will confirm shipment window shortly.\n\n"
                f"Best regards,\n{settings.company_name} Order Desk\n"
                f"{_draft_footer(settings)}\n"
            ),
        }
        amt = float(amounts[0]["amount"]) if amounts else 0.0
        crm_deal = {
            "title": f"PO {order_refs[0] if order_refs else 'inbound'} — {company}",
            "amount": amt,
            "currency": (amounts[0].get("currency") if amounts else "USD") or "USD",
            "stage": "qualified",
            "source": "email",
            "quote_ref": order_refs[0] if order_refs else None,
            "contact_email": contact_email,
            "notes": "PO acknowledgment staged from email",
        }
        task_drafts.append(
            {
                "title": f"Fulfill {order_refs[0] if order_refs else 'inbound PO'}",
                "description": f"Process PO from {company}. Refs: {', '.join(order_refs) or 'n/a'}.",
                "assignee": "Ops Fulfillment",
                "priority": "high",
                "due_days": 1,
                "kind": intent,
            }
        )
        apply_defaults["crm_deal"] = True

    elif intent == INVOICE_PAYMENT:
        amt_lines = "\n".join(
            f"  • {a.get('raw') or a.get('amount')} {a.get('currency', 'USD')}" for a in amounts
        ) or "  • (amounts not detected — please verify)"
        email_draft = {
            "to": contact_email,
            "cc": "",
            "subject": f"Re: {email.subject} — Finance received",
            "body": (
                f"Dear {contact_name},\n\n"
                f"We received your invoice/payment note"
                f"{(' regarding ' + ', '.join(order_refs)) if order_refs else ''}.\n\n"
                f"Extracted amounts:\n{amt_lines}\n\n"
                f"Our finance team will reconcile and follow up if anything is needed.\n\n"
                f"Best regards,\n{settings.company_name} Finance\n"
                f"{_draft_footer(settings)}\n"
            ),
        }
        task_drafts.append(
            {
                "title": f"Finance reconcile — {company}",
                "description": (
                    f"Reconcile invoice/payment from {contact_email}. "
                    f"Amounts: {amounts}. Refs: {order_refs}."
                ),
                "assignee": "Finance",
                "priority": "high" if critical else "medium",
                "due_days": 2,
                "kind": intent,
            }
        )

    elif intent == SHIPPING_STATUS:
        email_draft = {
            "to": contact_email,
            "cc": "",
            "subject": f"Re: {email.subject} — Shipment update",
            "body": (
                f"Dear {contact_name},\n\n"
                f"Thank you for checking on delivery"
                f"{(' for ' + ', '.join(order_refs)) if order_refs else ''}.\n\n"
                f"Standard lead time for in-stock items is 7–10 business days. "
                f"Our logistics team is verifying the latest carrier status and will "
                f"share tracking as soon as it is available.\n\n"
                f"KB refs: {', '.join(r['ref'] for r in kb_refs) or 'KB-LEADTIMES'}.\n\n"
                f"Best regards,\n{settings.company_name} Logistics\n"
                f"{_draft_footer(settings)}\n"
            ),
        }
        task_drafts.append(
            {
                "title": f"Update shipping status — {', '.join(order_refs) or company}",
                "description": f"Pull carrier ETA for {company} / {order_refs}.",
                "assignee": "Logistics",
                "priority": "high" if critical else "medium",
                "due_days": 1,
                "kind": intent,
            }
        )

    elif intent == PRODUCT_INFO:
        email_draft = {
            "to": contact_email,
            "cc": "",
            "subject": f"Re: {email.subject} — Product information",
            "body": (
                f"Dear {contact_name},\n\n"
                f"Thanks for your interest in our catalog. "
                f"We can share datasheets, availability, and COA documentation on request.\n\n"
                f"References: {', '.join(r['ref'] for r in kb_refs) or 'KB-CATALOG, KB-DATASHEETS'}.\n"
                f"Please reply with SKUs or product families you need and we will attach the files.\n\n"
                f"Best regards,\n{settings.company_name} Product Support\n"
                f"{_draft_footer(settings)}\n"
            ),
        }
        task_drafts.append(
            {
                "title": f"Send catalog/COA pack — {company}",
                "description": f"Attach datasheets/COA for inquiry from {contact_name}.",
                "assignee": "Sales Ops",
                "priority": "medium",
                "due_days": 2,
                "kind": intent,
            }
        )

    elif intent in {SUPPORT_COMPLAINT, ESCALATION}:
        escalate = critical or intent == ESCALATION
        email_draft = {
            "to": contact_email,
            "cc": "",
            "subject": f"Re: {email.subject} — We are on it",
            "body": (
                f"Dear {contact_name},\n\n"
                f"Thank you for raising this with us — we take quality and service issues seriously.\n\n"
                f"We have opened an internal ticket and "
                f"{'escalated to a senior ops owner' if escalate else 'assigned our support team'}. "
                f"Next steps: we will investigate, propose a remedy (replacement, RMA, or credit), "
                f"and confirm timelines within one business day.\n\n"
                f"Best regards,\n{settings.company_name} Customer Success\n"
                f"{_draft_footer(settings)}\n"
            ),
        }
        ticket_draft = {
            "title": f"{'ESCALATION: ' if escalate else ''}{email.subject[:120]}",
            "description": email.body[:2000],
            "status": "escalated" if escalate else "open",
            "priority": "critical" if escalate else ("high" if critical else "medium"),
            "category": intent,
            "assignee": "Support Lead" if escalate else "Support",
            "escalate": escalate,
            "extracted": {"order_refs": order_refs, "company": company},
        }
        task_drafts.append(
            {
                "title": f"{'Escalate' if escalate else 'Resolve'} — {company}",
                "description": f"Handle {intent} from {contact_name}. Refs: {order_refs}.",
                "assignee": "Support Lead" if escalate else "Support",
                "priority": "critical" if escalate else "high",
                "due_days": 0 if escalate else 1,
                "kind": intent,
            }
        )
        apply_defaults["create_ticket"] = True
        if escalate:
            apply_defaults["crm_deal"] = False

    elif intent == MEETING_REQUEST:
        hint = meeting_hint or "times that work this week"
        email_draft = {
            "to": contact_email,
            "cc": "",
            "subject": f"Re: {email.subject} — Scheduling",
            "body": (
                f"Dear {contact_name},\n\n"
                f"Happy to connect. You mentioned {hint}. "
                f"Please pick a 30-minute slot or reply with two alternatives and we will confirm.\n\n"
                f"We can cover product fit, lead times, and commercial terms on the call.\n\n"
                f"Best regards,\n{settings.company_name} Sales\n"
                f"{_draft_footer(settings)}\n"
            ),
        }
        task_drafts.append(
            {
                "title": f"Schedule meeting — {company}",
                "description": f"Calendar note: meeting request from {contact_name} ({hint}).",
                "assignee": "Sales",
                "priority": "medium",
                "due_days": 1,
                "kind": intent,
            }
        )

    elif intent == CONTRACT_PARTNERSHIP:
        email_draft = {
            "to": contact_email,
            "cc": "",
            "subject": f"Re: {email.subject} — Received",
            "body": (
                f"Dear {contact_name},\n\n"
                f"Thank you for sharing the contract / NDA / partnership request. "
                f"Our commercial + legal review queue has been notified. "
                f"We typically respond within 3–5 business days with redlines or next steps.\n\n"
                f"Best regards,\n{settings.company_name} Partnerships\n"
                f"{_draft_footer(settings)}\n"
            ),
        }
        task_drafts.append(
            {
                "title": f"Legal/ops review — {company}",
                "description": f"Review NDA/MSA/partnership request from {contact_name}.",
                "assignee": "Legal Ops",
                "priority": "high",
                "due_days": 3,
                "kind": intent,
            }
        )

    elif intent == VENDOR_ONBOARDING:
        email_draft = {
            "to": contact_email,
            "cc": "",
            "subject": f"Re: {email.subject} — Onboarding packet",
            "body": (
                f"Dear {contact_name},\n\n"
                f"We can complete vendor onboarding promptly. Typical packet includes W-9, "
                f"insurance certificate, banking details, and compliance attestations "
                f"(see KB-VENDOR / KB-COMPLIANCE).\n\n"
                f"Reply with your preferred portal link or attached forms and we will prioritize.\n\n"
                f"Best regards,\n{settings.company_name} Supplier Ops\n"
                f"{_draft_footer(settings)}\n"
            ),
        }
        task_drafts.append(
            {
                "title": f"Vendor compliance checklist — {company}",
                "description": f"Collect W-9 / insurance / compliance docs for {company}.",
                "assignee": "Compliance",
                "priority": "medium",
                "due_days": 5,
                "kind": intent,
            }
        )

    else:
        # general_ops / other_business
        email_draft = {
            "to": contact_email,
            "cc": "",
            "subject": f"Re: {email.subject}",
            "body": (
                f"Dear {contact_name},\n\n"
                f"Thank you for your message. We have logged this with our operations team "
                f"and will follow up with a clear response shortly.\n\n"
                f"Best regards,\n{settings.company_name}\n"
                f"{_draft_footer(settings)}\n"
            ),
        }
        task_drafts.append(
            {
                "title": f"Review inbound — {company}",
                "description": f"Review and respond to: {email.subject}",
                "assignee": "Ops",
                "priority": "low" if not critical else "high",
                "due_days": 2,
                "kind": intent,
            }
        )

    title = f"{suggested.get('label') or INTENT_LABELS.get(intent, intent)} — {company}"
    return {
        "intent": intent,
        "workflow": workflow,
        "title": title,
        "actions": suggested.get("actions") or [],
        "kb_refs": kb_refs,
        "order_refs": order_refs,
        "amounts": amounts,
        "quote_draft": quote_draft,
        "email_draft": email_draft,
        "crm_contact_draft": crm_contact,
        "crm_deal_draft": crm_deal,
        "ticket_draft": ticket_draft,
        "task_drafts": task_drafts,
        "apply_defaults": apply_defaults,
        "attention_label": attention,
        "escalate": critical or intent == ESCALATION,
    }


def _draft_quote_email(quote: dict[str, Any], *, original_subject: str, settings: Any) -> dict[str, Any]:
    lines = []
    for item in quote.get("line_items") or []:
        lines.append(
            f"  • {item['quantity']} × {item['name']} ({item['sku']}) "
            f"@ ${item['unit_price']:.2f}/{item['unit']} = ${item['line_total']:.2f}"
        )
    items_block = "\n".join(lines) if lines else "  (no matched catalog lines — please review)"
    amend = " amended" if quote.get("amendment") else ""
    body = (
        f"Dear {quote.get('contact_name')},\n\n"
        f"Thank you for your inquiry. Please find{amend} quotation {quote.get('quote_ref')} "
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
        f"{_draft_footer(settings)}\n"
    )
    return {
        "to": quote.get("contact_email"),
        "cc": "",
        "subject": f"Re: {original_subject} — Quote {quote.get('quote_ref')}",
        "body": body,
    }
