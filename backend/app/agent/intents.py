"""Research-backed B2B inbound intents and proposed-action catalog.

Cyberfield BAS classifies every business email into one of these intents,
auto-extracts fields, and stages an action plan up to the human approval gate.
Nothing customer-facing (send, CRM write, ticket close) runs without approval.
"""

from __future__ import annotations

from typing import Any

# ── Canonical intents (agency ops package) ──────────────────────────────────
RFQ_QUOTE = "rfq_quote"                      # RFQ / quote / price inquiry / tender / RFP
PURCHASE_ORDER = "purchase_order"            # PO / order confirmation / reorder
INVOICE_PAYMENT = "invoice_payment"          # Invoice / payment / billing / remittance
SHIPPING_STATUS = "shipping_status"          # Shipping / delivery / tracking / lead time
PRODUCT_INFO = "product_info"                # Availability / catalog / datasheet / COA
SUPPORT_COMPLAINT = "support_complaint"      # Support / complaint / quality / return-RMA
ESCALATION = "escalation"                    # Escalation / cancel threat / VIP / legal-ish
MEETING_REQUEST = "meeting_request"          # Meeting / demo / call scheduling
CONTRACT_PARTNERSHIP = "contract_partnership"  # Contract / NDA / partnership
CHANGE_ORDER = "change_order"                # Change order / amend quote
VENDOR_ONBOARDING = "vendor_onboarding"      # Vendor onboarding / compliance (light)
GENERAL_OPS = "general_ops"
OTHER_BUSINESS = "other_business"

ALL_INTENTS = (
    RFQ_QUOTE,
    PURCHASE_ORDER,
    INVOICE_PAYMENT,
    SHIPPING_STATUS,
    PRODUCT_INFO,
    SUPPORT_COMPLAINT,
    ESCALATION,
    MEETING_REQUEST,
    CONTRACT_PARTNERSHIP,
    CHANGE_ORDER,
    VENDOR_ONBOARDING,
    GENERAL_OPS,
    OTHER_BUSINESS,
)

_LEGACY_MAP = {
    "quote_request": RFQ_QUOTE,
    "catalog_inquiry": PRODUCT_INFO,
    "invoice_po": INVOICE_PAYMENT,
    "general": OTHER_BUSINESS,
}

INTENT_LABELS: dict[str, str] = {
    RFQ_QUOTE: "RFQ / Quote / Tender",
    PURCHASE_ORDER: "Purchase Order / Reorder",
    INVOICE_PAYMENT: "Invoice / Payment",
    SHIPPING_STATUS: "Shipping / Delivery",
    PRODUCT_INFO: "Product / Catalog / COA",
    SUPPORT_COMPLAINT: "Support / Complaint / RMA",
    ESCALATION: "Escalation / VIP / Legal",
    MEETING_REQUEST: "Meeting / Demo / Call",
    CONTRACT_PARTNERSHIP: "Contract / NDA / Partnership",
    CHANGE_ORDER: "Change Order / Amend Quote",
    VENDOR_ONBOARDING: "Vendor Onboarding / Compliance",
    GENERAL_OPS: "General Ops",
    OTHER_BUSINESS: "Other Business",
}

SUGGESTED_ACTION_LABELS: dict[str, str] = {
    RFQ_QUOTE: "Draft quote + stage CRM deal",
    PURCHASE_ORDER: "Confirm order + stage CRM + ops task",
    INVOICE_PAYMENT: "Extract amounts + finance task",
    SHIPPING_STATUS: "Draft status reply + logistics task",
    PRODUCT_INFO: "Draft catalog/COA reply + KB refs",
    SUPPORT_COMPLAINT: "Draft apology + support ticket",
    ESCALATION: "Escalate ticket + draft careful reply",
    MEETING_REQUEST: "Draft scheduling reply + calendar note",
    CONTRACT_PARTNERSHIP: "Draft reply + legal/ops review task",
    CHANGE_ORDER: "Draft amended quote + CRM update",
    VENDOR_ONBOARDING: "Draft onboarding reply + compliance checklist",
    GENERAL_OPS: "Draft ops reply + task",
    OTHER_BUSINESS: "Review + optional reply",
}

WORKFLOW_BY_INTENT: dict[str, str] = {
    RFQ_QUOTE: "quote_from_email",
    PURCHASE_ORDER: "order_confirm",
    INVOICE_PAYMENT: "invoice_ops",
    SHIPPING_STATUS: "shipping_reply",
    PRODUCT_INFO: "product_info_reply",
    SUPPORT_COMPLAINT: "support_reply",
    ESCALATION: "escalation_reply",
    MEETING_REQUEST: "meeting_reply",
    CONTRACT_PARTNERSHIP: "contract_review",
    CHANGE_ORDER: "change_order",
    VENDOR_ONBOARDING: "vendor_onboarding",
    GENERAL_OPS: "general_ops",
    OTHER_BUSINESS: "general_ops",
}

# Actions that require human approval before execution
APPROVAL_GATED = frozenset({
    "send_outbound",
    "crm_create",
    "crm_update",
    "ticket_close",
})


def normalize_intent(raw: str | None) -> str:
    if not raw:
        return OTHER_BUSINESS
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    if key in _LEGACY_MAP:
        return _LEGACY_MAP[key]
    if key in ALL_INTENTS:
        return key
    return OTHER_BUSINESS


def _base_actions(intent: str, *, attention_label: str) -> list[str]:
    """Propose concrete actions staged pending human approval."""
    critical = (attention_label or "").lower() == "critical"
    actions: list[str] = ["classify", "extract", "attention_rank"]

    plans: dict[str, list[str]] = {
        RFQ_QUOTE: [
            "draft_quote", "draft_reply", "stage_crm_deal", "stage_crm_contact",
            "catalog_price_lookup", "followup_task",
        ],
        PURCHASE_ORDER: [
            "extract_po_refs", "draft_order_ack", "stage_crm_deal",
            "stage_crm_contact", "ops_fulfillment_task",
        ],
        INVOICE_PAYMENT: [
            "extract_amounts", "extract_po_refs", "finance_task", "draft_ack_reply",
        ],
        SHIPPING_STATUS: [
            "extract_order_refs", "draft_status_reply", "logistics_task", "kb_lead_time_ref",
        ],
        PRODUCT_INFO: [
            "catalog_lookup", "kb_datasheet_ref", "draft_info_reply", "sales_task",
        ],
        SUPPORT_COMPLAINT: [
            "draft_apology_reply", "create_support_ticket", "qa_task",
        ],
        ESCALATION: [
            "create_escalation_ticket", "draft_careful_reply", "notify_manager_task",
        ],
        MEETING_REQUEST: [
            "draft_scheduling_reply", "calendar_task_note", "stage_crm_contact",
        ],
        CONTRACT_PARTNERSHIP: [
            "draft_ack_reply", "legal_ops_review_task", "stage_crm_contact",
        ],
        CHANGE_ORDER: [
            "extract_change_lines", "draft_amended_quote", "draft_reply",
            "stage_crm_update", "followup_task",
        ],
        VENDOR_ONBOARDING: [
            "draft_onboarding_reply", "compliance_checklist_task", "stage_crm_contact",
        ],
        GENERAL_OPS: ["draft_reply", "ops_task"],
        OTHER_BUSINESS: ["draft_optional_reply", "review_task"],
    }
    actions.extend(plans.get(intent, plans[OTHER_BUSINESS]))

    if critical or intent == ESCALATION:
        if "escalate" not in actions:
            actions.append("escalate")
    # Gate markers (executed only on approve)
    actions.append("await_human_approval")
    return actions


def suggested_action_for(
    intent: str,
    *,
    attention_label: str = "Low",
    confidence: float = 0.7,
) -> dict[str, Any]:
    intent = normalize_intent(intent)
    actions = _base_actions(intent, attention_label=attention_label)
    escalate = "escalate" in actions
    return {
        "intent": intent,
        "label": SUGGESTED_ACTION_LABELS.get(intent, INTENT_LABELS.get(intent, intent)),
        "intent_label": INTENT_LABELS.get(intent, intent),
        "actions": actions,
        "escalate": escalate,
        "confidence": round(float(confidence), 3),
        "workflow": WORKFLOW_BY_INTENT.get(intent, "general_ops"),
        "approval_gated": sorted(APPROVAL_GATED),
    }


def intent_matrix() -> list[dict[str, Any]]:
    """Capabilities matrix for docs / dashboard."""
    rows = []
    for intent in ALL_INTENTS:
        sa = suggested_action_for(intent, attention_label="High", confidence=0.85)
        rows.append({
            "intent": intent,
            "label": sa["intent_label"],
            "proposed_action": sa["label"],
            "actions": sa["actions"],
            "workflow": sa["workflow"],
        })
    return rows
