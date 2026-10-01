"""Inbox + Gmail sync endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EmailOut, GmailStatusOut, GmailSyncResponse
from app.services.gmail import gmail_connection_status, sync_inbox

router = APIRouter(tags=["inbox"])


@router.get("/inbox/gmail/status", response_model=GmailStatusOut)
def gmail_status():
    return gmail_connection_status()


@router.post("/inbox/sync", response_model=GmailSyncResponse)
async def sync_gmail_inbox(db: Session = Depends(get_db)):
    """Sync Gmail into inbox. Classifies intents and stages action plans for approval."""
    result = await sync_inbox(db)
    filtered_n = int(result.get("filtered") or result.get("filtered_count") or 0)
    return GmailSyncResponse(
        mode=result["mode"],
        imported=result["imported"],
        skipped=result["skipped"],
        filtered=filtered_n,
        filtered_count=filtered_n,
        filtered_subjects=list(result.get("filtered_subjects") or []),
        classified=int(result.get("classified") or 0),
        plans_staged=int(result.get("plans_staged") or 0),
        emails=[EmailOut.model_validate(e) for e in result["emails"]],
        status=GmailStatusOut.model_validate(result["status"]),
        warning=result.get("warning"),
        attention_rescored=int(result.get("attention_rescored") or 0),
        list_query=result.get("list_query"),
    )


@router.post("/gmail/sync", response_model=GmailSyncResponse, include_in_schema=False)
async def sync_gmail_alias(db: Session = Depends(get_db)):
    return await sync_gmail_inbox(db)
