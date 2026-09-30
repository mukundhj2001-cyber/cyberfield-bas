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


class TaskOut(OrmModel):
    id: int
    title: str
    description: str
    status: str
    assignee: str
    priority: str
    related_deal_id: Optional[int] = None
    related_email_id: Optional[int] = None
    created_at: datetime
    due_at: Optional[datetime] = None


class ApprovalOut(OrmModel):
    id: int
    email_id: int
    workflow: str
    status: str
    quote_draft: dict[str, Any]
    email_draft: dict[str, Any]
    agent_trace: Optional[list[dict[str, Any]]] = None
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None
    email: Optional[EmailOut] = None


class QuoteRunRequest(BaseModel):
    email_id: Optional[int] = None
    message_id: Optional[str] = None


class QuoteRunResponse(BaseModel):
    approval_id: int
    email_id: int
    status: str
    quote_draft: dict[str, Any]
    email_draft: dict[str, Any]
    agent_trace: list[dict[str, Any]]
    llm_mode: str


class ApprovalDecisionRequest(BaseModel):
    reviewed_by: str = "Ops Manager"
    review_note: Optional[str] = None
    quote_draft: Optional[dict[str, Any]] = None
    email_draft: Optional[dict[str, Any]] = None


class ActivityOut(OrmModel):
    id: int
    kind: str
    message: str
    meta: Optional[dict[str, Any]] = None
    created_at: datetime


class DashboardStats(BaseModel):
    emails_total: int
    emails_unread: int
    approvals_pending: int
    deals_open: int
    tasks_open: int
    products: int
    recent_activity: list[ActivityOut] = Field(default_factory=list)
    llm_mode: str


class GmailStatusOut(BaseModel):
    mode: str
    connected: bool
    label: str
    detail: str
    oauth_configured: bool = False


class GmailSyncResponse(BaseModel):
    mode: str
    imported: int
    skipped: int
    emails: list[EmailOut] = Field(default_factory=list)
    status: GmailStatusOut
    warning: Optional[str] = None


class N8nEmailWebhook(BaseModel):
    from_address: str
    subject: str
    body: str
    from_name: Optional[str] = ""
    to_address: Optional[str] = "quotes@northwind-industrial.example"
    message_id: Optional[str] = None
    run_quote_workflow: bool = False


class N8nTriggerQuote(BaseModel):
    email_id: Optional[int] = None
    message_id: Optional[str] = None


class N8nEmailWebhookResponse(BaseModel):
    email_id: int
    message_id: str
    status: str
    workflow: Optional[QuoteRunResponse] = None


class WebhookInfoOut(BaseModel):
    email_path: str
    trigger_quote_path: str
    secret_required: bool
    secret_header: str
    sample_email_payload: dict[str, Any]
    sample_trigger_payload: dict[str, Any]
    notes: str
