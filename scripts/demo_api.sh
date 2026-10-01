#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:8000}"
echo "== health =="
curl -s "$API/health" | python3 -m json.tool
echo "== gmail status =="
curl -s "$API/inbox/gmail/status" | python3 -m json.tool
echo "== sync gmail (mock) — classify + stage plans =="
curl -s -X POST "$API/inbox/sync" -o /tmp/bas_sync.json
python3 -m json.tool < /tmp/bas_sync.json
python3 - <<'PY'
import json
sync = json.load(open("/tmp/bas_sync.json"))
filtered = int(sync.get("filtered_count") if sync.get("filtered_count") is not None else sync.get("filtered") or 0)
classified = int(sync.get("classified") or 0)
staged = int(sync.get("plans_staged") or 0)
print(f"filtered non-business: {filtered}")
print(f"classified: {classified}")
print(f"plans_staged: {staged}")
subjects = " | ".join(sync.get("filtered_subjects") or [])
if subjects:
    print("filtered subjects:", subjects)
if filtered:
    print("OK: business filter dropped noise on sync")
else:
    print("NOTE: filtered=0 (noise already seen or pool empty) — continuing")
if staged or classified:
    print("OK: intent classify / plan staging active")
PY
echo "== inbox ranked by attention (business only) =="
curl -s "$API/emails?sort=attention" -o /tmp/bas_emails.json
python3 - <<'PY'
import json
rows = json.load(open("/tmp/bas_emails.json"))
print(f"{len(rows)} business messages (attention desc):")
intents = set()
for e in rows:
    label = e.get("attention_label", "?")
    score = float(e.get("attention_score") or 0)
    intent = e.get("intent") or "unclassified"
    intents.add(intent)
    biz = e.get("business_relevant", True)
    assert biz is True or biz == 1, f"non-business leaked into inbox: {e['subject']}"
    sa = (e.get("suggested_action") or {}).get("label") or "-"
    print(f"  {label:8} {score:5.1f}  [{intent:22}] {e['subject'][:50]}  → {sa[:40]}")
    low = (e.get("subject") or "").lower()
    assert "newsletter" not in low and "reddit" not in low and "linkedin" not in low, (
        f"noise subject in inbox: {e['subject']}"
    )
scores = [float(e.get("attention_score") or 0) for e in rows]
assert scores == sorted(scores, reverse=True), "emails not sorted by attention desc"
assert len(intents) >= 2, f"expected diverse intents, got {intents}"
print("OK: attention sort + multi-intent inbox; intents:", ", ".join(sorted(intents)))
PY

echo "== seed diversity via n8n ingest (idempotent) =="
for payload in \
  '{"from_address":"recv@lakeside.example","from_name":"Priya","subject":"Where is shipment for PO-3890? Need tracking ETA","body":"Please share tracking and delivery status for PO-3890. Lead time update needed.","message_id":"demo-ship-1","run_ops_workflow":true}' \
  '{"from_address":"qa@summit.example","from_name":"Alex","subject":"Quality complaint damaged seal kit need RMA","body":"Defective NW-SEAL-KIT arrived damaged. Unacceptable. Open RMA and refund.","message_id":"demo-rma-1","run_ops_workflow":true}' \
  '{"from_address":"ap@coastal.example","from_name":"AP","subject":"Remittance INV-2201 paid $3240 via ACH","body":"Invoice INV-2201 remittance $3,240.00 USD ACH. PO-4100.","message_id":"demo-inv-1","run_ops_workflow":true}' \
  '{"from_address":"buyer@river.example","from_name":"Jordan","subject":"PO-4412 released please confirm order","body":"Purchase order PO-4412 released ($4860). Please confirm order acknowledgment.","message_id":"demo-po-1","run_ops_workflow":true}' \
  '{"from_address":"legal@harbor.example","from_name":"Morgan","subject":"NDA partnership MSA draft for review","body":"Please review our NDA and master supply agreement for partnership.","message_id":"demo-nda-1","run_ops_workflow":true}'
do
  curl -s -X POST "$API/webhooks/n8n/email" -H 'Content-Type: application/json' -d "$payload" \
    | python3 -c 'import sys,json; r=json.load(sys.stdin); w=r.get("workflow") or {}; print(r.get("status"), r.get("intent"), w.get("approval_id"), "filtered" if r.get("filtered") else "")'
done

echo "== ensure action plans staged (ops/run on unread if needed) =="
python3 - <<'PY2'
import json, os, urllib.request
API = os.environ.get("API", "http://localhost:8000")
emails = json.load(urllib.request.urlopen(API + "/emails?sort=attention"))
approvals = json.load(urllib.request.urlopen(API + "/approvals?status=pending"))
print(f"emails={len(emails)} pending_approvals={len(approvals)}")
pending_ids = {a.get("email_id") for a in approvals}
if len(approvals) < 3:
    for e in emails:
        if e.get("status") in ("unread", "action_staged") and e["id"] not in pending_ids:
            req = urllib.request.Request(
                API + "/workflows/ops/run",
                data=json.dumps({"email_id": e["id"]}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                r = json.load(urllib.request.urlopen(req))
                print("staged", e["id"], r.get("intent"), r.get("approval_id"))
            except Exception as ex:
                print("skip", e["id"], ex)
approvals = json.load(urllib.request.urlopen(API + "/approvals?status=pending"))
print(f"pending after ensure: {len(approvals)}")
assert len(approvals) >= 1, "expected staged approvals"
intents = {e.get("intent") for e in emails if e.get("intent")}
print("inbox intents:", ", ".join(sorted(i for i in intents if i)))
assert len(intents) >= 2, f"expected diverse intents, got {intents}"
print("OK: multi-intent coverage verified")
PY2

echo "== approvals queue =="
curl -s "$API/approvals?status=pending" -o /tmp/bas_approvals.json
python3 - <<'PY'
import json
rows = json.load(open("/tmp/bas_approvals.json"))
print(f"pending approvals: {len(rows)}")
types = {r.get("action_type") for r in rows}
print("action types:", ", ".join(sorted(t for t in types if t)) or "(none)")
assert len(rows) >= 1, "expected at least one staged approval after sync"
print("OK: unified approvals queue populated")
# Prefer RFQ or support so approve proves CRM/ticket writes
prefer = ("rfq_quote", "support_complaint", "purchase_order", "change_order")
pick = next((r for r in rows if r.get("action_type") in prefer), rows[0])
AID = pick["id"]
print(f"approving #{AID} intent={pick.get('action_type')}")
open("/tmp/bas_aid.txt","w").write(str(AID))
PY
AID=$(cat /tmp/bas_aid.txt)
echo "== approve $AID (selective apply) =="
curl -s -X POST "$API/approvals/$AID/approve" -H 'Content-Type: application/json' \
  -d '{"reviewed_by":"Ops Manager","review_note":"Demo approve multi-intent plan","apply_flags":{"send_outbound":true,"crm_contact":true,"crm_deal":true,"create_ticket":true,"create_tasks":true}}' \
  | tee /tmp/bas_approve.json | python3 -m json.tool
echo "== dashboard pipeline =="
curl -s "$API/dashboard/stats" -o /tmp/bas_stats.json
python3 - <<'PY'
import json
s = json.load(open("/tmp/bas_stats.json"))
print("pipeline:", s.get("pipeline"))
print("by_intent:", s.get("by_intent"))
print("intent_matrix rows:", len(s.get("intent_matrix") or []))
assert len(s.get("intent_matrix") or []) >= 10, "intent matrix too thin"
print("OK: multi-action dashboard + intent matrix")
PY
echo "== n8n noise ingest should filter (reddit/medium/substack/github/newsletter) =="
python3 - <<'PY'
import json, os, urllib.request
API = os.environ.get("API", "http://localhost:8000")
samples = [
  {"from_address":"noreply@redditmail.com","from_name":"Reddit","subject":"Reddit weekly digest","body":"Unsubscribe from this newsletter roundup.","run_ops_workflow":False,"message_id":"demo-noise-reddit"},
  {"from_address":"noreply@medium.com","from_name":"Medium","subject":"Stories for you from Medium","body":"Read this article. Top stories. Unsubscribe.","run_ops_workflow":False,"message_id":"demo-noise-medium"},
  {"from_address":"noreply@substack.com","from_name":"Substack","subject":"Your Substack digest","body":"Weekly newsletter digest. Manage preferences.","run_ops_workflow":False,"message_id":"demo-noise-substack"},
  {"from_address":"notifications@github.com","from_name":"GitHub","subject":"[GitHub] You have new notifications","body":"github notifications. Pushed to main.","run_ops_workflow":False,"message_id":"demo-noise-github"},
  {"from_address":"digest@industry-weekly.example","from_name":"Industry Weekly","subject":"This week in industrial supply — newsletter","body":"Daily digest morning brief. Unsubscribe.","run_ops_workflow":False,"message_id":"demo-noise-newsletter"},
]
for s in samples:
    req = urllib.request.Request(
        API + "/webhooks/n8n/email",
        data=json.dumps(s).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    r = json.load(urllib.request.urlopen(req))
    assert r.get("filtered") is True, (s["subject"], r)
    print("OK filtered:", s["subject"][:48], r.get("filter_reasons"))
print("OK: all noisy n8n samples filtered")
PY
echo "== sync response reports filtered_count =="
python3 - <<'PY'
import json
sync = json.load(open("/tmp/bas_sync.json"))
fc = sync.get("filtered_count", sync.get("filtered"))
assert fc is not None, sync
print(f"OK: sync filtered_count={fc} filtered={sync.get('filtered')} subjects={sync.get('filtered_subjects')}")
PY
echo "== n8n support complaint + ops workflow =="
WH=$(curl -s -X POST "$API/webhooks/n8n/email" \
  -H 'Content-Type: application/json' \
  -d '{"from_address":"qa@acme.example","from_name":"QA Lead","subject":"Quality complaint — defective seal kit need RMA","body":"Received damaged NW-SEAL-KIT. Unacceptable. Please open RMA and refund.","run_ops_workflow":true}')
echo "$WH" | python3 -m json.tool
echo "== deals / tasks / tickets =="
curl -s "$API/crm/deals" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("deals", len(d))'
curl -s "$API/tasks" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("tasks", len(d))'
curl -s "$API/tickets" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("tickets", len(d))'
echo "== smoke complete =="
