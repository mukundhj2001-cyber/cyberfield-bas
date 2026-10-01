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
| Ranking | Attention score + Critical/High/Medium/Low on **business** mail |
| Filter | Business-relevance heuristics (offline) · optional domain allowlist |

Optional Postgres via `docker-compose.yml` (Docker not required for the local demo).

## Repository layout

```
cyberfield-bas/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py / schemas.py / database.py / seed.py
│   │   ├── agent/           # llm + quote_workflow
│   │   ├── services/        # gmail.py + attention.py + business_relevance.py
│   │   └── routers/         # emails, inbox, workflows, approvals, crm, tasks, webhooks, dashboard
│   └── requirements.txt
├── frontend/                # Dark ops UI (Cyberfield branding)
├── examples/n8n/            # Sample n8n workflow JSON
├── scripts/
│   ├── demo_api.sh
│   └── gmail_oauth_refresh_token.py
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

1. **Inbox** — **business mail only**, sorted by **attention** (Critical → Low). Click **Sync Gmail** to import mock RFQs (noise digests are filtered).
2. Use the **Priority** chips to filter Critical / High / Medium / Low.
3. Select a high-attention RFQ → **Run quote workflow**.
4. **Approvals** — review line items / edit qty or email body.
5. Click **Approve & send (mock)**.
6. **CRM** — contact + deal at `quote_sent`; **Tasks** — follow-up assigned to Sales Ops.
7. **Dashboard** — activity feed shows `gmail_sync` / `email_sent` / `crm_update` / `task_created`.
8. **Workflows** — copy n8n webhook URLs + sample payload.

API-only path:

```bash
# Mock Gmail sync (+ attention rescore)
curl -s -X POST http://localhost:8000/inbox/sync | python -m json.tool

# Inbox sorted by attention (default)
curl -s 'http://localhost:8000/emails?sort=attention' | python -m json.tool

# Filter by priority label
curl -s 'http://localhost:8000/emails?priority=Critical' | python -m json.tool

# Process highest-attention unread (omit body) or a specific email
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

## Attention ranking

Every inbox message stores:

| Field | Meaning |
|-------|---------|
| `attention_score` | 0–100 composite score |
| `attention_label` | `Critical` (≥70) · `High` (≥50) · `Medium` (≥30) · `Low` (<30) |
| `attention_meta` | Factor breakdown + human-readable reasons |

**Scoring factors**

| Factor | Signals (examples) | Cap |
|--------|--------------------|-----|
| Urgency language | ASAP, urgent, EOD, deadline dates, “needed by/within” | 30 |
| RFQ / quote intent | RFQ, quote, please quote, quantities | 25 |
| Estimated deal value | Catalog SKU×qty or `$` amounts in body | 25 |
| Age / unread | Unread, fresh (<6h), stale unread (>24h / >72h) | 15 |
| Escalation | escalate, complaint, cancel, legal, CEO/VP, production down | 20 |

**When scores recompute**

- On seed / app startup (existing DBs migrate columns + rescore)
- After every `POST /inbox/sync` (full inbox)
- On external ingest (`POST /webhooks/n8n/email`)
- After quote workflow extract (uses matched line items for value)
- Manually: `POST /emails/recompute-attention`

Inbox UI defaults to attention-desc sort with rank chips and an optional priority filter. Mock/seeded mail is written with varied urgency so demos show a clear Critical → Low ordering.

## Business relevance filter

Inbox is **business-only**. On every ingest path (mock Gmail sync, OAuth sync, n8n webhook) a heuristic classifier decides whether a message is B2B ops mail worth attention. Noise is **not imported** (preferred) so Reddit digests, newsletters, LinkedIn/X promos, and similar clutter never land in the default list.

| Signal type | Examples |
|-------------|----------|
| **Keep** | RFQ, quote, invoice, PO, procurement, supplier/vendor, order, shipment, SLA, contract, demo request, known CRM contacts, `BUSINESS_EMAIL_DOMAINS` allowlist |
| **Drop** | Reddit, newsletter, unsubscribe, LinkedIn/Twitter/X marketing, promo, no-reply digests, weekly roundup / media digests |

Attention ranking (Critical / High / ...) still runs **only on business mail** after import.

**Knobs** (env / `backend/.env`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `BUSINESS_FILTER_ENABLED` | `true` | Set `false` to import everything (debug) |
| `BUSINESS_EMAIL_DOMAINS` | empty | Comma-separated domains always treated as business |
| `BUSINESS_FILTER_USE_LLM` | `false` | Reserved for optional LLM refinement when a real provider is keyed |

Sync response includes `filtered` + `filtered_subjects`; the Inbox UI shows a **filtered N non-business** chip after sync. Seeded mock pool includes 1-2 noise samples that are dropped on sync to prove the feature. Legacy rows already in SQLite are reclassified on API boot and hidden from the default inbox (`business_relevant=false`).

Debug: `GET /emails?include_non_business=true` lists hidden rows if any were marked rather than dropped.

## Mock vs real matrix

| Capability | Status |
|------------|--------|
| Inbox UI + quote workflow + approvals | **Real** (API + UI) |
| Attention ranking | **Real** (heuristic scorer, business mail only) |
| Business filter | **Real** (heuristics; noise not imported) |
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
| **oauth** | `GMAIL_MODE=oauth` + `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` + `GOOGLE_REFRESH_TOKEN` | `users.messages.list` + `get` → idempotent import (`gmail-{id}`); falls back to mock on failure |

UI chip / `GET /inbox/gmail/status`: **Mock** vs **Connected**. Never commit secrets — copy `.env.example` → `backend/.env`.

#### Real Gmail setup (refresh token)

1. In [Google Cloud Console](https://console.cloud.google.com/): create/select a project → enable **Gmail API**.
2. APIs & Services → Credentials → **Create OAuth client ID** → Application type **Desktop app**. Copy Client ID + Client Secret (or download the JSON).
3. Configure the OAuth consent screen (External / Testing is fine for personal use). Add your Google account as a test user if the app is in Testing.
4. Generate a refresh token locally (browser consent; readonly scope only):

```bash
python scripts/gmail_oauth_refresh_token.py \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET
# or:  --client-secrets ./client_secret.json
```

5. Paste into `backend/.env` (do **not** commit):

```env
GMAIL_MODE=oauth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
```

6. Restart the API. Confirm `GET /inbox/gmail/status` shows `"connected": true`, `"label": "Connected"`.
7. `POST /inbox/sync` imports recent inbox mail idempotently and re-ranks attention.

Scope used: `https://www.googleapis.com/auth/gmail.readonly`. If Google returns no `refresh_token`, revoke the app at https://myaccount.google.com/permissions and re-run the script (it requests `prompt=consent` + `access_type=offline`).

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
- `GET /emails` (`?sort=attention|received|id`, `?priority=Critical|High|Medium|Low`, `?include_non_business=true`)
- `POST /emails/recompute-attention`
- `GET /emails/{id}`, `POST /emails/{id}/recompute-attention`
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

# Smoke sync + ranking order (API must be running)
bash scripts/demo_api.sh
```

## Branding

Product: **Cyberfield Business Automation System** / short **Cyberfield BAS**  
Sample company: **Northwind Industrial** (fictional).  
UI style: dark ops dashboard (visual reference only — not Futurion or any third-party product name/logo).
