#!/usr/bin/env bash
# Real worker lifecycle: mock path by default; pass --live for billable Vultr test.
set -eu
BASE="${GHOSTRANGE_BASE_URL:-http://127.0.0.1}"
BASE="${BASE%/}"
LIVE=0
for arg in "$@"; do
  case "$arg" in
    --live) LIVE=1 ;;
  esac
done

echo "== guardrails =="
curl -fsS "$BASE/v1/scheduler/guardrails" | python3 -m json.tool

echo "== compute dry-check =="
DRY=$(curl -fsS "$BASE/v1/scheduler/compute-dry-check" || true)
echo "$DRY" | python3 -m json.tool 2>/dev/null || echo "$DRY"
BEFORE=$(echo "$DRY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('owned_worker_count',''))" 2>/dev/null || echo "")
if [[ "$LIVE" == "1" ]]; then
  OK=$(echo "$DRY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok', False))" 2>/dev/null || echo False)
  if [[ "$OK" != "True" && "$OK" != "true" ]]; then
    echo "STOP: live test requires working Vultr API (fix IP ACL / VPC first)"
    exit 1
  fi
fi
if [[ -n "$BEFORE" && "$BEFORE" != "0" && "$BEFORE" != "None" ]]; then
  echo "STOP: owned_worker_count=$BEFORE (clean up first)"
  exit 1
fi

RID=$(python3 -c 'import uuid; print(uuid.uuid4())')
if [[ "$LIVE" == "1" ]]; then
  echo "== LIVE worker test range_id=$RID =="
  RESULT=$(curl -fsS -X POST "$BASE/v1/scheduler/live-worker-test?range_id=$RID&live=true&confirm=true")
else
  echo "== mock worker-benchmark range_id=$RID =="
  RESULT=$(curl -fsS -X POST "$BASE/v1/scheduler/worker-benchmark?range_id=$RID")
fi
echo "$RESULT" | python3 -m json.tool

AFTER=$(curl -fsS "$BASE/v1/scheduler/compute-dry-check" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('owned_worker_count',''))" 2>/dev/null || echo "")
if [[ -z "$AFTER" || "$AFTER" == "None" ]]; then
  AFTER=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('owned_workers_after',''))" 2>/dev/null || echo "")
fi
echo "owned_worker_count after=$AFTER"
if [[ -n "$AFTER" && "$AFTER" != "0" ]]; then
  echo "FAIL: workers still owned"
  exit 1
fi

echo "$RESULT" | python3 -c "
import json, sys
r = json.load(sys.stdin)
for k in ('run_id','worker_id','task_id','evidence_artifact_id','owned_workers_after'):
    print(f'{k}={r.get(k)}')
"

echo "PASS real-worker-e2e live=$LIVE"
