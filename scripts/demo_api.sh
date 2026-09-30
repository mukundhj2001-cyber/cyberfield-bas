#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:8000}"
echo "== health =="
curl -s "$API/health" | python3 -m json.tool
echo "== run quote on email 1 =="
RESULT=$(curl -s -X POST "$API/workflows/quote/run" -H 'Content-Type: application/json' -d '{"email_id":1}')
echo "$RESULT" | python3 -m json.tool
AID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['approval_id'])")
echo "== approve $AID =="
curl -s -X POST "$API/approvals/$AID/approve" -H 'Content-Type: application/json' \
  -d '{"reviewed_by":"Ops Manager","review_note":"Demo approve"}' | python3 -m json.tool
echo "== deals =="
curl -s "$API/crm/deals" | python3 -m json.tool
echo "== tasks =="
curl -s "$API/tasks" | python3 -m json.tool
