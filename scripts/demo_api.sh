#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:8000}"
echo "== health =="
curl -s "$API/health" | python3 -m json.tool
echo "== gmail status =="
curl -s "$API/inbox/gmail/status" | python3 -m json.tool
echo "== sync gmail (mock) =="
curl -s -X POST "$API/inbox/sync" | python3 -m json.tool
echo "== inbox ranked by attention =="
curl -s "$API/emails?sort=attention" -o /tmp/bas_emails.json
python3 - <<'PY'
import json
rows = json.load(open("/tmp/bas_emails.json"))
print(f"{len(rows)} messages (attention desc):")
for e in rows:
    label = e.get("attention_label", "?")
    score = float(e.get("attention_score") or 0)
    print(f"  {label:8} {score:5.1f}  {e['subject'][:70]}")
scores = [float(e.get("attention_score") or 0) for e in rows]
assert scores == sorted(scores, reverse=True), "emails not sorted by attention desc"
labels = {e.get("attention_label") for e in rows}
assert len(labels) >= 2, f"expected varied attention labels for demo, got {labels}"
print("OK: attention sort order verified; labels:", ", ".join(sorted(labels)))
PY
echo "== filter Critical/High =="
curl -s "$API/emails?priority=Critical" | python3 -c 'import sys,json; print("Critical:", len(json.load(sys.stdin)))'
curl -s "$API/emails?priority=High" | python3 -c 'import sys,json; print("High:", len(json.load(sys.stdin)))'
echo "== n8n webhook ingest + auto quote =="
WH=$(curl -s -X POST "$API/webhooks/n8n/email" \
  -H 'Content-Type: application/json' \
  -d '{"from_address":"buyer@acme.example","from_name":"Alex Buyer","subject":"RFQ — NW-BRG-6205 x 50","body":"Please quote 50 x NW-BRG-6205 bearings for plant maintenance.","run_quote_workflow":true}')
echo "$WH" | python3 -m json.tool
AID=$(echo "$WH" | python3 -c "import sys,json; w=json.load(sys.stdin); print(w.get('workflow',{}).get('approval_id') or '')")
if [[ -n "$AID" ]]; then
  echo "== approve $AID =="
  curl -s -X POST "$API/approvals/$AID/approve" -H 'Content-Type: application/json' \
    -d '{"reviewed_by":"Ops Manager","review_note":"Demo approve via n8n path"}' | python3 -m json.tool
fi
echo "== deals =="
curl -s "$API/crm/deals" | python3 -m json.tool
echo "== tasks =="
curl -s "$API/tasks" | python3 -m json.tool
