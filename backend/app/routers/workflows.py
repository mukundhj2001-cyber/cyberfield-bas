from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.quote_workflow import QuoteWorkflowError, run_quote_from_email
from app.database import get_db
from app.schemas import QuoteRunRequest, QuoteRunResponse

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/quote/run", response_model=QuoteRunResponse)
async def run_quote_workflow(payload: QuoteRunRequest, db: Session = Depends(get_db)):
    try:
        result = await run_quote_from_email(
            db, email_id=payload.email_id, message_id=payload.message_id
        )
        return result
    except QuoteWorkflowError as exc:
        raise HTTPException(400, str(exc)) from exc
