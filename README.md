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
| Ingest | **Mock Gmail sync** (default) · optional Google OAuth · **n8n webhooks** |

Optional Postgres via `docker-compose.yml` (Docker not required for the local demo).

## Repository layout

```
cyberfield-bas/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py / schemas.py / database.py / seed.py
│   │   ├── agent/           # llm + quote_workflow
│   │   ├── services/gmail.py
│   │   └── routers/         # emails, inbox, workflows, approvals, crm, tasks, webhooks, dashboard
│   └── requirements.txt
├── frontend/                # Dark ops UI (Cyberfield branding)
├── examples/n8n/            # Sample n8n workflow JSON
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv
# Windows PowerShell:  python -m venv .venv ; .\.venv\Scripts\Activate.ps1
source .venv/bin/activate
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

### 3. Demo script (mock LLM + mock Gmail, offline)

1. **Inbox** — click **Sync Gmail** (imports demo Gmail-like RFQs) or open a seeded RFQ.
2. Click **Run quote workflow**.
3. **Approvals** — review line items / edit qty or email body.
4. Click **Approve & send (mock)**.
5. **CRM** — contact + deal at `quote_sent`; **Tasks** — follow-up assigned to Sales Ops.
6. **Dashboard** — activity feed shows `gmail_sync` / `email_sent` / `crm_update` / `task_created`.
7. **Workflows** — copy n8n webhook URLs + sample payload.

API-only path:

```bash
# Mock Gmail sync
curl -s -X POST http://localhost:8000/inbox/sync | python -m json.tool

# Process first unread / specific email
curl -s -X POST http://localhost:8000/workflows/quote/run \
  -H 'Content-Type: application/json' -d '{"email_id":1}'

# n8n-style ingest (optionally start quote workflow)
curl -s -X POST http://localhost:8000/webhooks/n8n/email \
  -H 'Content-Type: application/json' \
  -d '{"from_address":"buyer@acme.example","from_name":"Alex Buyer","subject":"RFQ — NW-BRG-6205 x 50","body":"Please quote 50 x NW-BRG-6205 bearings.","run_quote_workflow":true}'

# Approve (replace ID)
curl -s -X POST http://localhost:8000/approvals/1/approve \
  -H 'Content-Type: application/json' \
  -d '{"reviewed_by":"Ops Manager"}'
```

Or: `bash scripts/demo_api.sh`

## Mock vs real matrix

| Capability | Status |
|------------|--------|
| Inbox UI + quote workflow + approvals | **Real** (API + UI) |
| Pricing catalog / CRM / tasks writes | **Real** (SQLite) |
| LLM extraction | **Mock by default**; optional OpenAI/Anthropic |
| Gmail sync | **Mock by default** (seeded pool); optional OAuth |
| Outbound email send | **Mock** (activity log `email_sent`) |
| n8n webhooks | **Real** HTTP endpoints; secret optional |
| Postgres | Optional via Compose; SQLite is default |

### Gmail: mock vs OAuth

| Mode | When | Behavior |
|------|------|----------|
| **mock** (default) | `GMAIL_MODE=mock` or OAuth env incomplete | `POST /inbox/sync` imports stable demo messages (`gmail-mock-00*`) idempotently |
| **oauth** | `GMAIL_MODE=oauth` + `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` + `GOOGLE_REFRESH_TOKEN` | Lists recent Gmail inbox via API; falls back to mock on failure |

Never commit secrets. Copy `.env.example` → `backend/.env`.

**OAuth setup (optional):** create a Google Cloud OAuth client (Desktop or Web), obtain a refresh token with Gmail readonly scope (`https://www.googleapis.com/auth/gmail.readonly`), set the three env vars, set `GMAIL_MODE=oauth`, restart the API. Status: `GET /inbox/gmail/status`.

### LLM: mock vs real

| Mode | When | Behavior |
|------|------|----------|
| **mock** (default) | No keys, or `LLM_PROVIDER=mock` | Deterministic keyword extract over catalog SKUs |
| **openai** / **anthropic** | API key set | Live extract; failures fall back to mock |

### n8n integration

| Endpoint | Purpose |
|----------|---------|
| `GET /webhooks/n8n/info` | URLs, sample payload, whether secret is required |
| `POST /webhooks/n8n/email` | Body: `from_address`, `subject`, `body`, optional `run_quote_workflow` |
| `POST /webhooks/n8n/trigger-quote` | Body: `email_id` or `message_id` → starts quote workflow |

Optional header: `X-Webhook-Secret` matching `N8N_WEBHOOK_SECRET`. When the env var is **unset**, webhooks are open for local demo.

Import `examples/n8n/gmail-to-bas.json` into n8n (Gmail Trigger → HTTP Request). If n8n runs in Docker and BAS on the host, use `http://host.docker.internal:8000/...`.

## API surface

- `GET /health`
- `GET /dashboard/stats`
- `GET /emails`, `GET /emails/{id}`
- `GET /inbox/gmail/status`, `POST /inbox/sync` (alias `POST /gmail/sync`)
- `POST /workflows/quote/run`
- `GET /approvals`, `POST /approvals/{id}/approve|reject`
- `GET /crm/contacts`, `/crm/deals`, `/crm/products`
- `GET /tasks`
- `GET /webhooks/n8n/info`, `POST /webhooks/n8n/email`, `POST /webhooks/n8n/trigger-quote`

## Build checks

```bash
# Frontend
cd frontend && npm run build

# Backend import
cd backend && source .venv/bin/activate && python -c "from app.main import app"
```

## Branding

Product: **Cyberfield Business Automation System** / short **Cyberfield BAS**  
Sample company: **Northwind Industrial** (fictional).  
UI style: dark ops dashboard (visual reference only — not Futurion or any third-party product name/logo).
