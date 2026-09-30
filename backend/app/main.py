from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.llm import resolve_llm_mode
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import approvals, crm, dashboard, emails, inbox, tasks, webhooks, workflows
from app.seed import seed_if_empty
from app.services.gmail import gmail_connection_status


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


settings = get_settings()
app = FastAPI(
    title="Cyberfield Business Automation System",
    description="Autonomous business operations agent — quote-from-email flagship workflow.",
    version="0.2.0",
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
        "n8n_secret_required": bool(settings.n8n_webhook_secret),
    }
