from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.intents import intent_matrix
from app.agent.llm import resolve_llm_mode
from app.database import get_db
from app.models import ActivityLog, Approval, Deal, Email, Product, Task, Ticket
from app.schemas import ActivityOut, DashboardStats, IntentMatrixRow

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db)):
    recent = db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(16).all()
    biz = Email.business_relevant.is_(True)
    emails = db.query(Email).filter(biz).all()
    by_intent: dict[str, int] = {}
    for e in emails:
        key = e.intent or "unclassified"
        by_intent[key] = by_intent.get(key, 0) + 1

    pipeline = {
        "inbox_unread": db.query(Email).filter(biz, Email.status == "unread").count(),
        "action_staged": db.query(Email).filter(biz, Email.status == "action_staged").count(),
        "approvals_pending": db.query(Approval).filter(Approval.status == "pending").count(),
        "approvals_approved": db.query(Approval).filter(Approval.status == "approved").count(),
        "tickets_open": db.query(Ticket).filter(Ticket.status.in_(["open", "in_progress", "escalated"])).count(),
        "tasks_open": db.query(Task).filter(Task.status.in_(["open", "in_progress"])).count(),
        "deals_open": db.query(Deal).filter(Deal.stage.in_(["qualified", "quote_sent"])).count(),
    }

    return DashboardStats(
        emails_total=len(emails),
        emails_unread=pipeline["inbox_unread"],
        approvals_pending=pipeline["approvals_pending"],
        deals_open=pipeline["deals_open"],
        tasks_open=pipeline["tasks_open"],
        tickets_open=pipeline["tickets_open"],
        products=db.query(Product).count(),
        by_intent=by_intent,
        pipeline=pipeline,
        recent_activity=[ActivityOut.model_validate(a) for a in recent],
        llm_mode=resolve_llm_mode(),
        intent_matrix=[IntentMatrixRow(**row) for row in intent_matrix()],
    )
