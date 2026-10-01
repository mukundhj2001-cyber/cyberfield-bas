from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.ops_workflow import OpsWorkflowError, run_ops_plan, run_quote_from_email
from app.database import get_db
from app.schemas import OpsRunRequest, QuoteRunRequest, QuoteRunResponse

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _to_response(result: dict) -> QuoteRunResponse:
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


@router.post("/ops/run", response_model=QuoteRunResponse)
async def run_ops_workflow(payload: OpsRunRequest, db: Session = Depends(get_db)):
    """Classify + extract + draft action plan; stage pending approval by default."""
    try:
        result = await run_ops_plan(
            db,
            email_id=payload.email_id,
            message_id=payload.message_id,
            auto_stage=payload.auto_stage,
        )
        return _to_response(result)
    except OpsWorkflowError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/quote/run", response_model=QuoteRunResponse)
async def run_quote_workflow(payload: QuoteRunRequest, db: Session = Depends(get_db)):
    """Back-compat — runs full ops plan (RFQ and all other intents)."""
    try:
        result = await run_quote_from_email(
            db, email_id=payload.email_id, message_id=payload.message_id
        )
        return _to_response(result)
    except OpsWorkflowError as exc:
        raise HTTPException(400, str(exc)) from exc
