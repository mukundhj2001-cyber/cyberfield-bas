from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.llm import resolve_llm_mode
from app.config import get_settings
from app.database import Base, SessionLocal, engine, ensure_schema
from app.routers import approvals, crm, dashboard, emails, inbox, tasks, tickets, webhooks, workflows
from app.seed import seed_if_empty
from app.services.attention import recompute_all
from app.services.business_relevance import reclassify_existing_emails
from app.services.gmail import gmail_connection_status


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db = SessionLocal()
    try:
        seed_if_empty(db)
        reclassify_existing_emails(db)
        recompute_all(db)
    finally:
        db.close()
    yield


settings = get_settings()
app = FastAPI(
    title="Cyberfield Business Automation System",
    description=(
        "Agency-grade inbound ops package — classify B2B email intents, "
        "auto-extract, draft replies/quotes, stage CRM/tickets/tasks, "
        "human approval before any outbound send or CRM write."
    ),
    version="0.5.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(emails.router)
app.include_router(inbox.router)
app.include_router(workflows.router)
app.include_router(approvals.router)
app.include_router(crm.router)
app.include_router(tasks.router)
app.include_router(tickets.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    gmail = gmail_connection_status()
    return {
        "status": "ok",
        "brand": settings.brand_name,
        "company": settings.company_name,
        "llm_mode": resolve_llm_mode(),
        "gmail_mode": gmail["mode"],
        "gmail_connected": gmail["connected"],
        "n8n_secret_required": bool(settings.n8n_webhook_secret),
        "version": "0.5.0",
        "capabilities": "multi_intent_ops",
    }
