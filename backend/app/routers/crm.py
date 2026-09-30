from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Contact, Deal, Product
from app.schemas import ContactOut, DealOut, ProductOut

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(db: Session = Depends(get_db)):
    return db.query(Contact).order_by(Contact.created_at.desc()).all()


@router.get("/deals", response_model=list[DealOut])
def list_deals(db: Session = Depends(get_db)):
    return (
        db.query(Deal)
        .options(joinedload(Deal.contact))
        .order_by(Deal.created_at.desc())
        .all()
    )


@router.get("/deals/{deal_id}", response_model=DealOut)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    deal = (
        db.query(Deal).options(joinedload(Deal.contact)).filter(Deal.id == deal_id).first()
    )
    if not deal:
        raise HTTPException(404, "Deal not found")
    return deal


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.sku.asc()).all()
