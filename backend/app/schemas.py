from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmailOut(OrmModel):
    id: int
    message_id: str
    from_address: str
    from_name: str
    to_address: str
    subject: str
    body: str
    received_at: datetime
    status: str
    intent: Optional[str] = None
    extracted: Optional[dict[str, Any]] = None
    suggested_action: Optional[dict[str, Any]] = None
    attention_score: float = 0.0
    attention_label: str = "Low"
    attention_meta: Optional[dict[str, Any]] = None
    business_relevant: bool = True
    business_meta: Optional[dict[str, Any]] = None


class ProductOut(OrmModel):
    id: int
    sku: str
    name: str
    description: str
    unit_price: float
    unit: str
    category: str
    in_stock: int


class ContactOut(OrmModel):
    id: int
    name: str
    email: str
    company: str
    phone: str
    created_at: datetime


class DealOut(OrmModel):
    id: int
    title: str
    contact_id: Optional[int] = None
    amount: float
    currency: str
    stage: str
    source: str
    quote_ref: Optional[str] = None
    notes: str
    created_at: datetime
    updated_at: datetime
    contact: Optional[ContactOut] = None


class TicketOut(OrmModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    category: str
    assignee: str
    related_email_id: Optional[int] = None
    related_approval_id: Optional[int] = None
    escalate: bool = False
    extracted: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class TaskOut(OrmModel):
    id: int
    title: str
    description: str
    status: str
    assignee: str
    priority: str
    kind: str = "general"
    related_deal_id: Optional[int] = None
    related_email_id: Optional[int] = None
    related_ticket_id: Optional[int] = None
    created_at: datetime
    due_at: Optional[datetime] = None


class ApprovalOut(OrmModel):
    id: int
    email_id: int
    workflow: str
    action_type: Optional[str] = None
    title: Optional[str] = None
    status: str
    quote_draft: dict[str, Any] = Field(default_factory=dict)
    email_draft: dict[str, Any] = Field(default_factory=dict)
    action_plan: Optional[dict[str, Any]] = None
    apply_defaults: Optional[dict[str, Any]] = None
    agent_trace: Optional[list[dict[str, Any]]] = None
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None
    email: Optional[EmailOut] = None


class QuoteRunRequest(BaseModel):
    email_id: Optional[int] = None
    message_id: Optional[str] = None


class OpsRunRequest(BaseModel):
    email_id: Optional[int] = None
    message_id: Optional[str] = None
    auto_stage: bool = True


class QuoteRunResponse(BaseModel):
    approval_id: Optional[int] = None
    email_id: int
    status: str
    intent: Optional[str] = None
    workflow: Optional[str] = None
    title: Optional[str] = None
    quote_draft: dict[str, Any] = Field(default_factory=dict)
    email_draft: dict[str, Any] = Field(default_factory=dict)
    action_plan: Optional[dict[str, Any]] = None
    suggested_action: Optional[dict[str, Any]] = None
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    llm_mode: str = "mock"


class ApprovalDecisionRequest(BaseModel):
    reviewed_by: str = "Ops Manager"
    review_note: Optional[str] = None
    quote_draft: Optional[dict[str, Any]] = None
    email_draft: Optional[dict[str, Any]] = None
    # Selective apply — omit to use approval.apply_defaults
    apply_flags: Optional[dict[str, bool]] = None


class ActivityOut(OrmModel):
    id: int
    kind: str
    message: str
    meta: Optional[dict[str, Any]] = None
    created_at: datetime


class IntentMatrixRow(BaseModel):
    intent: str
    label: str
    proposed_action: str
    actions: list[str]
    workflow: str


class DashboardStats(BaseModel):
    emails_total: int
    emails_unread: int
    approvals_pending: int
    deals_open: int
    tasks_open: int
    tickets_open: int = 0
    products: int
    by_intent: dict[str, int] = Field(default_factory=dict)
    pipeline: dict[str, int] = Field(default_factory=dict)
    recent_activity: list[ActivityOut] = Field(default_factory=list)
    llm_mode: str
    intent_matrix: list[IntentMatrixRow] = Field(default_factory=list)


class GmailStatusOut(BaseModel):
    mode: str
    connected: bool
    label: str
    detail: str
    oauth_configured: bool = False
    requested_mode: Optional[str] = None
    scope: Optional[str] = None
    hint: Optional[str] = None


class GmailSyncResponse(BaseModel):
    mode: str
    imported: int
    skipped: int
    filtered: int = 0
    filtered_subjects: list[str] = Field(default_factory=list)
    classified: int = 0
    plans_staged: int = 0
    emails: list[EmailOut] = Field(default_factory=list)
    status: GmailStatusOut
    warning: Optional[str] = None
    attention_rescored: int = 0


class N8nEmailWebhook(BaseModel):
    from_address: str
    subject: str
    body: str
    from_name: Optional[str] = ""
    to_address: Optional[str] = "quotes@northwind-industrial.example"
    message_id: Optional[str] = None
    run_quote_workflow: bool = False
    run_ops_workflow: bool = False


class N8nTriggerQuote(BaseModel):
    email_id: Optional[int] = None
    message_id: Optional[str] = None


class N8nEmailWebhookResponse(BaseModel):
    email_id: Optional[int] = None
    message_id: Optional[str] = None
    status: str
    filtered: bool = False
    filter_reasons: list[str] = Field(default_factory=list)
    intent: Optional[str] = None
    suggested_action: Optional[dict[str, Any]] = None
    workflow: Optional[QuoteRunResponse] = None


class WebhookInfoOut(BaseModel):
    email_path: str
    trigger_quote_path: str
    trigger_ops_path: str = "/webhooks/n8n/trigger-ops"
    secret_required: bool
    secret_header: str
    sample_email_payload: dict[str, Any]
    sample_trigger_payload: dict[str, Any]
    notes: str
