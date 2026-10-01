from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Email
from app.schemas import EmailOut
from app.services.attention import recompute_all, recompute_one

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=list[EmailOut])
def list_emails(
    db: Session = Depends(get_db),
    priority: Optional[str] = Query(
        default=None,
        description="Filter by attention_label: Critical|High|Medium|Low (case-insensitive)",
    ),
    sort: str = Query(
        default="attention",
        description="Sort: attention (default) | received | id",
    ),
    include_non_business: bool = Query(
        default=False,
        description="When true, include messages marked non-business (default inbox hides them)",
    ),
):
    q = db.query(Email)
    if not include_non_business:
        q = q.filter(Email.business_relevant.is_(True))
    if priority:
        q = q.filter(Email.attention_label.ilike(priority.strip()))
    if sort == "received":
        q = q.order_by(Email.received_at.desc(), Email.id.desc())
    elif sort == "id":
        q = q.order_by(Email.id.desc())
    else:
        # Default: most attention first, then freshest (business mail only)
        q = q.order_by(Email.attention_score.desc(), Email.received_at.desc(), Email.id.desc())
    return q.all()


@router.get("/{email_id}", response_model=EmailOut)
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(404, "Email not found")
    return email


@router.post("/recompute-attention")
def recompute_attention(db: Session = Depends(get_db)):
    """Force re-score of all business inbox messages (demo / ops tool)."""
    count = recompute_all(db)
    return {"recomputed": count}


@router.post("/{email_id}/recompute-attention", response_model=EmailOut)
def recompute_one_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(404, "Email not found")
    recompute_one(db, email)
    return email
