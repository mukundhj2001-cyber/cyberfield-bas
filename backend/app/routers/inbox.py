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
    """Sync Gmail into inbox. Uses mock pool unless OAuth credentials are configured."""
    result = await sync_inbox(db)
    return GmailSyncResponse(
        mode=result["mode"],
        imported=result["imported"],
        skipped=result["skipped"],
        emails=[EmailOut.model_validate(e) for e in result["emails"]],
        status=GmailStatusOut.model_validate(result["status"]),
        warning=result.get("warning"),
    )


# Alias path for discoverability
@router.post("/gmail/sync", response_model=GmailSyncResponse, include_in_schema=False)
async def sync_gmail_alias(db: Session = Depends(get_db)):
    return await sync_gmail_inbox(db)
