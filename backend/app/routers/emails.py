from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Email
from app.schemas import EmailOut

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=list[EmailOut])
def list_emails(db: Session = Depends(get_db)):
    return db.query(Email).order_by(Email.received_at.desc(), Email.id.desc()).all()


@router.get("/{email_id}", response_model=EmailOut)
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(404, "Email not found")
    return email
