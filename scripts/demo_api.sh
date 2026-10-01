#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:8000}"
echo "== health =="
curl -s "$API/health" | python3 -m json.tool
echo "== gmail status =="
curl -s "$API/inbox/gmail/status" | python3 -m json.tool
echo "== sync gmail (mock) =="
curl -s -X POST "$API/inbox/sync" -o /tmp/bas_sync.json
python3 -m json.tool < /tmp/bas_sync.json
python3 - <<'PY'
import json
sync = json.load(open("/tmp/bas_sync.json"))
filtered = int(sync.get("filtered") or 0)
print(f"filtered non-business: {filtered}")
subjects = " | ".join(sync.get("filtered_subjects") or [])
if subjects:
    print("filtered subjects:", subjects)
if filtered:
    print("OK: business filter dropped noise on sync")
else:
    print("NOTE: filtered=0 (noise already seen or pool empty) — continuing")
PY
echo "== inbox ranked by attention (business only) =="
curl -s "$API/emails?sort=attention" -o /tmp/bas_emails.json
python3 - <<'PY'
import json
rows = json.load(open("/tmp/bas_emails.json"))
print(f"{len(rows)} business messages (attention desc):")
for e in rows:
    label = e.get("attention_label", "?")
    score = float(e.get("attention_score") or 0)
    biz = e.get("business_relevant", True)
    assert biz is True or biz == 1, f"non-business leaked into inbox: {e['subject']}"
    print(f"  {label:8} {score:5.1f}  {e['subject'][:70]}")
    low = (e.get("subject") or "").lower()
    assert "newsletter" not in low and "reddit" not in low and "linkedin" not in low, (
        f"noise subject in inbox: {e['subject']}"
    )
scores = [float(e.get("attention_score") or 0) for e in rows]
assert scores == sorted(scores, reverse=True), "emails not sorted by attention desc"
labels = {e.get("attention_label") for e in rows}
assert len(labels) >= 2, f"expected varied attention labels for demo, got {labels}"
print("OK: attention sort + business-only inbox verified; labels:", ", ".join(sorted(labels)))
PY
echo "== filter Critical/High =="
curl -s "$API/emails?priority=Critical" | python3 -c 'import sys,json; print("Critical:", len(json.load(sys.stdin)))'
curl -s "$API/emails?priority=High" | python3 -c 'import sys,json; print("High:", len(json.load(sys.stdin)))'
echo "== n8n noise ingest should filter =="
curl -s -X POST "$API/webhooks/n8n/email" \
  -H 'Content-Type: application/json' \
  -d '{"from_address":"noreply@redditmail.com","from_name":"Reddit","subject":"Reddit weekly digest","body":"Unsubscribe from this newsletter roundup.","run_quote_workflow":false}' \
  | tee /tmp/bas_noise.json | python3 -m json.tool
python3 - <<'PY'
import json
r = json.load(open("/tmp/bas_noise.json"))
assert r.get("filtered") is True, r
print("OK: n8n noise filtered", r.get("filter_reasons"))
PY
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
