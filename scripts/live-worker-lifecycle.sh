#!/usr/bin/env bash
# Steps 6–10: dry-check → one worker-benchmark → verify teardown (no secrets printed).
set -eu
BASE="${1:-http://127.0.0.1}"
BASE="${BASE%/}"

echo "== guardrails =="
curl -fsS "$BASE/v1/scheduler/guardrails" | python3 -m json.tool

echo "== compute dry-check (read-only) =="
curl -fsS "$BASE/v1/scheduler/compute-dry-check" | python3 -m json.tool

BEFORE=$(curl -fsS "$BASE/v1/scheduler/compute-dry-check" | python3 -c "import sys,json; print(json.load(sys.stdin)['owned_worker_count'])")
if [[ "$BEFORE" != "0" ]]; then
  echo "STOP: owned_worker_count=$BEFORE before benchmark (clean up in Vultr console first)"
  exit 1
fi

RID=$(python3 -c 'import uuid; print(uuid.uuid4())')
echo "== worker-benchmark range_id=$RID =="
RESULT=$(curl -fsS -X POST "$BASE/v1/scheduler/worker-benchmark?range_id=$RID")
echo "$RESULT" | python3 -m json.tool

AFTER=$(curl -fsS "$BASE/v1/scheduler/compute-dry-check" | python3 -c "import sys,json; print(json.load(sys.stdin)['owned_worker_count'])")
echo "owned_worker_count after=$AFTER"
if [[ "$AFTER" != "0" ]]; then
  echo "FAIL: workers still owned after benchmark"
  exit 1
fi

RUN_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['run_id'])")
echo "== postgres run row (via API list) =="
curl -fsS "$BASE/v1/scheduler/workers?range_id=$RID" | python3 -m json.tool

echo "PASS live-worker-lifecycle run_id=$RUN_ID"
