# Cyberfield Business Automation System (Cyberfield BAS)

Autonomous **business operations** agent / workflow platform — **not a chatbot**.

Flagship demo for sample tenant **Northwind Industrial**:

> Customer email requesting a quotation → classify/extract → check pricing DB → draft quote + email → **human approval** → on approve: log send, update CRM, assign task.

Built as a portfolio slice for [Cyberfield](https://github.com/mukundhj2001-cyber) / ops-automation demos.

## Stack

| Layer | Tech |
|--------|------|
| Backend | FastAPI · SQLAlchemy · SQLite (default) |
| Frontend | React · Vite · TypeScript · Tailwind v4 |
| Workflow | `quote_from_email` state machine (LangGraph-shaped stages) |
| LLM | OpenAI / Anthropic when keyed; otherwise **deterministic mock** |

Optional Postgres via `docker-compose.yml` (Docker not required for the local demo).

## Repository layout

```
cyberfield-bas/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + seed on startup
│   │   ├── models.py / schemas.py / database.py / seed.py
│   │   ├── agent/
│   │   │   ├── llm.py           # mock | openai | anthropic facade
│   │   │   └── quote_workflow.py
│   │   └── routers/             # emails, workflows, approvals, crm, tasks, dashboard
│   └── requirements.txt
├── frontend/                    # Vite React dark ops UI
├── docker-compose.yml           # optional Postgres
├── .env.example
└── README.md
```

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health: [http://localhost:8000/health](http://localhost:8000/health)  
Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### 3. Demo script (mock LLM, offline)

1. **Inbox** — open `RFQ — 6205 bearings…` (or the motor/VFD RFQ).
2. Click **Run quote workflow**.
3. **Approvals** — review line items / edit qty or email body.
4. Click **Approve & send (mock)**.
5. **CRM** — contact + deal at `quote_sent`; **Tasks** — follow-up assigned to Sales Ops.
6. **Dashboard** — activity feed shows email_sent / crm_update / task_created.

API-only path:

```bash
# Process first unread email
curl -s -X POST http://localhost:8000/workflows/quote/run -H 'Content-Type: application/json' -d '{}'

# Approve (replace ID)
curl -s -X POST http://localhost:8000/approvals/1/approve \
  -H 'Content-Type: application/json' \
  -d '{"reviewed_by":"Ops Manager"}'

curl -s http://localhost:8000/crm/deals | python -m json.tool
curl -s http://localhost:8000/tasks | python -m json.tool
```

## LLM: mock vs real

| Mode | When | Behavior |
|------|------|----------|
| **mock** (default) | No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, or `LLM_PROVIDER=mock` | Deterministic keyword extract over catalog SKUs — demo always works offline |
| **openai** | `OPENAI_API_KEY` set (and provider openai/auto) | Chat Completions JSON extract |
| **anthropic** | `ANTHROPIC_API_KEY` set | Messages API JSON extract |

Copy `.env.example` → `backend/.env` or export env vars. Real LLM failures fall back to mock so the demo never bricks.

## What is mock vs real in v1

| Capability | Status |
|------------|--------|
| Inbox / email send | **Mock** (seeded emails + activity log “email_sent”) |
| Pricing catalog | **Real** (SQLite seed) |
| Quote workflow + approvals | **Real** (API + UI) |
| CRM / tasks writes | **Real** (DB) |
| LLM extraction | **Mock by default**; optional OpenAI/Anthropic |
| Gmail / n8n / Twilio | **Not in v1** |
| Postgres | Optional via Compose; SQLite is default |

## API surface

- `GET /health`
- `GET /dashboard/stats`
- `GET /emails`, `GET /emails/{id}`
- `POST /workflows/quote/run` `{ "email_id"?: number }`
- `GET /approvals`, `GET /approvals/{id}`
- `POST /approvals/{id}/approve|reject`
- `GET /crm/contacts`, `/crm/deals`, `/crm/products`
- `GET /tasks`

## Build checks

```bash
# Frontend
cd frontend && npm run build

# Backend import
cd backend && source .venv/bin/activate && python -c "from app.main import app"
```

## Branding

Product: **Cyberfield Business Automation System** / short **Cyberfield BAS**  
Sample company: **Northwind Industrial** (fictional). Not CiteQA / FieldOps branding.
