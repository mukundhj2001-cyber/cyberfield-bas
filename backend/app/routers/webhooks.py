"""n8n / external webhook endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.agent.ops_workflow import OpsWorkflowError, run_ops_plan, run_quote_from_email
from app.config import get_settings
from app.database import get_db
from app.schemas import (
    N8nEmailWebhook,
    N8nEmailWebhookResponse,
    N8nTriggerQuote,
    QuoteRunResponse,
    WebhookInfoOut,
)
from app.services.gmail import ingest_external_email

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _check_secret(x_webhook_secret: Optional[str]) -> None:
    settings = get_settings()
    expected = settings.n8n_webhook_secret
    if not expected:
        return
    if not x_webhook_secret or x_webhook_secret != expected:
        raise HTTPException(401, "Invalid or missing X-Webhook-Secret")


def _to_wf(result: dict) -> QuoteRunResponse:
    return QuoteRunResponse(
        approval_id=result.get("approval_id"),
        email_id=result["email_id"],
        status=result.get("status") or "pending",
        intent=result.get("intent"),
        workflow=result.get("workflow"),
        title=result.get("title"),
        quote_draft=result.get("quote_draft") or {},
        email_draft=result.get("email_draft") or {},
        action_plan=result.get("action_plan"),
        suggested_action=result.get("suggested_action"),
        agent_trace=result.get("agent_trace") or [],
        llm_mode=result.get("llm_mode") or "mock",
    )


@router.get("/n8n/info", response_model=WebhookInfoOut)
def n8n_info():
    settings = get_settings()
    secret_required = bool(settings.n8n_webhook_secret)
    return WebhookInfoOut(
        email_path="/webhooks/n8n/email",
        trigger_quote_path="/webhooks/n8n/trigger-quote",
        trigger_ops_path="/webhooks/n8n/trigger-ops",
        secret_required=secret_required,
        secret_header="X-Webhook-Secret",
        sample_email_payload={
            "from_address": "buyer@example.com",
            "from_name": "Buyer Name",
            "subject": "RFQ — NW-BRG-6205 × 100",
            "body": "Please quote 100 × NW-BRG-6205 bearings.",
            "run_ops_workflow": True,
        },
        sample_trigger_payload={"email_id": 1},
        notes=(
            "Set N8N_WEBHOOK_SECRET to require X-Webhook-Secret. "
            "Ingest classifies intent + suggested action. "
            "Set run_ops_workflow=true to stage a full action plan for approval."
        ),
    )


@router.post("/n8n/email", response_model=N8nEmailWebhookResponse)
async def n8n_email(
    payload: N8nEmailWebhook,
    db: Session = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
):
    _check_secret(x_webhook_secret)
    result = await ingest_external_email(
        db,
        from_address=payload.from_address,
        from_name=payload.from_name or "",
        subject=payload.subject,
        body=payload.body,
        to_address=payload.to_address or "quotes@northwind-industrial.example",
        message_id=payload.message_id,
        source="n8n",
    )
    if isinstance(result, dict) and result.get("filtered"):
        return N8nEmailWebhookResponse(
            email_id=None,
            message_id=result.get("message_id"),
            status="filtered",
            filtered=True,
            filter_reasons=list(result.get("filter_reasons") or []),
            workflow=None,
        )

    email = result
    workflow_result = None
    run_ops = payload.run_ops_workflow or payload.run_quote_workflow
    if run_ops:
        try:
            workflow_result = await run_ops_plan(db, email_id=email.id)
        except OpsWorkflowError as exc:
            raise HTTPException(400, str(exc)) from exc

    return N8nEmailWebhookResponse(
        email_id=email.id,
        message_id=email.message_id,
        status=email.status,
        filtered=False,
        intent=email.intent,
        suggested_action=email.suggested_action,
        workflow=_to_wf(workflow_result) if workflow_result else None,
    )


@router.post("/n8n/trigger-quote", response_model=QuoteRunResponse)
@router.post("/n8n/trigger-ops", response_model=QuoteRunResponse)
async def n8n_trigger_ops(
    payload: N8nTriggerQuote,
    db: Session = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
):
    _check_secret(x_webhook_secret)
    try:
        result = await run_quote_from_email(
            db, email_id=payload.email_id, message_id=payload.message_id
        )
        return _to_wf(result)
    except OpsWorkflowError as exc:
        raise HTTPException(400, str(exc)) from exc
