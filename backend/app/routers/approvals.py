from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.agent.quote_workflow import QuoteWorkflowError, approve_quote, reject_quote
from app.database import get_db
from app.models import Approval
from app.schemas import ApprovalDecisionRequest, ApprovalOut

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
def list_approvals(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Approval).options(joinedload(Approval.email)).order_by(Approval.id.desc())
    if status:
        q = q.filter(Approval.status == status)
    return q.all()


@router.get("/{approval_id}", response_model=ApprovalOut)
def get_approval(approval_id: int, db: Session = Depends(get_db)):
    approval = (
        db.query(Approval)
        .options(joinedload(Approval.email))
        .filter(Approval.id == approval_id)
        .first()
    )
    if not approval:
        raise HTTPException(404, "Approval not found")
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
def approve(approval_id: int, payload: ApprovalDecisionRequest, db: Session = Depends(get_db)):
    try:
        return approve_quote(
            db,
            approval_id,
            reviewed_by=payload.reviewed_by,
            review_note=payload.review_note,
            quote_draft=payload.quote_draft,
            email_draft=payload.email_draft,
        )
    except QuoteWorkflowError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
def reject(approval_id: int, payload: ApprovalDecisionRequest, db: Session = Depends(get_db)):
    try:
        return reject_quote(
            db,
            approval_id,
            reviewed_by=payload.reviewed_by,
            review_note=payload.review_note,
        )
    except QuoteWorkflowError as exc:
        raise HTTPException(400, str(exc)) from exc
