"""n8n / external webhook endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.agent.quote_workflow import QuoteWorkflowError, run_quote_from_email
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
        return  # open in demo mode when secret unset
    if not x_webhook_secret or x_webhook_secret != expected:
        raise HTTPException(401, "Invalid or missing X-Webhook-Secret")


@router.get("/n8n/info", response_model=WebhookInfoOut)
def n8n_info():
    settings = get_settings()
    secret_required = bool(settings.n8n_webhook_secret)
    return WebhookInfoOut(
        email_path="/webhooks/n8n/email",
        trigger_quote_path="/webhooks/n8n/trigger-quote",
        secret_required=secret_required,
        secret_header="X-Webhook-Secret",
        sample_email_payload={
            "from_address": "buyer@example.com",
            "from_name": "Buyer Name",
            "subject": "RFQ — NW-BRG-6205 × 100",
            "body": "Please quote 100 × NW-BRG-6205 bearings.",
            "run_quote_workflow": False,
        },
        sample_trigger_payload={"email_id": 1},
        notes=(
            "Set N8N_WEBHOOK_SECRET in backend .env to require the X-Webhook-Secret header. "
            "When unset, webhooks are open for local demo. "
            "Point an n8n Gmail Trigger → HTTP Request node at POST /webhooks/n8n/email."
        ),
    )


@router.post("/n8n/email", response_model=N8nEmailWebhookResponse)
async def n8n_email(
    payload: N8nEmailWebhook,
    db: Session = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
):
    _check_secret(x_webhook_secret)
    email = ingest_external_email(
        db,
        from_address=payload.from_address,
        from_name=payload.from_name or "",
        subject=payload.subject,
        body=payload.body,
        to_address=payload.to_address or "quotes@northwind-industrial.example",
        message_id=payload.message_id,
        source="n8n",
    )
    workflow_result = None
    if payload.run_quote_workflow:
        try:
            workflow_result = await run_quote_from_email(db, email_id=email.id)
        except QuoteWorkflowError as exc:
            raise HTTPException(400, str(exc)) from exc

    return N8nEmailWebhookResponse(
        email_id=email.id,
        message_id=email.message_id,
        status=email.status,
        workflow=QuoteRunResponse(**workflow_result) if workflow_result else None,
    )


@router.post("/n8n/trigger-quote", response_model=QuoteRunResponse)
async def n8n_trigger_quote(
    payload: N8nTriggerQuote,
    db: Session = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
):
    _check_secret(x_webhook_secret)
    try:
        result = await run_quote_from_email(
            db, email_id=payload.email_id, message_id=payload.message_id
        )
        return result
    except QuoteWorkflowError as exc:
        raise HTTPException(400, str(exc)) from exc
