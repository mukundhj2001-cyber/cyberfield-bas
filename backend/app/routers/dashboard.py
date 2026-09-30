from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.llm import resolve_llm_mode
from app.database import get_db
from app.models import ActivityLog, Approval, Deal, Email, Product, Task
from app.schemas import ActivityOut, DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db)):
    recent = db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(12).all()
    return DashboardStats(
        emails_total=db.query(Email).count(),
        emails_unread=db.query(Email).filter(Email.status == "unread").count(),
        approvals_pending=db.query(Approval).filter(Approval.status == "pending").count(),
        deals_open=db.query(Deal).filter(Deal.stage.in_(["qualified", "quote_sent"])).count(),
        tasks_open=db.query(Task).filter(Task.status.in_(["open", "in_progress"])).count(),
        products=db.query(Product).count(),
        recent_activity=[ActivityOut.model_validate(a) for a in recent],
        llm_mode=resolve_llm_mode(),
    )
