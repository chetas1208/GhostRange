#!/usr/bin/env bash
# Phase 8 production checklist (run on ghostrange-control or against public URL).
set -eu
BASE="${1:-http://127.0.0.1}"
BASE="${BASE%/}"
pass=0
fail=0
check() {
  local name=$1
  shift
  if "$@"; then
    echo "[PASS] $name"
    pass=$((pass + 1))
  else
    echo "[FAIL] $name"
    fail=$((fail + 1))
  fi
}

check "frontend loads" sh -c "curl -fsS '$BASE/' | grep -qi '<html'"
check "health live" sh -c "curl -fsS '$BASE/health/live' | grep -q '\"ok\"'"
check "health ready" sh -c "curl -fsS '$BASE/health/ready' | grep -q '\"ok\"'"
check "dependencies matrix" sh -c "curl -fsS '$BASE/v1/production/dependencies' | grep -q postgres_durable"
check "postgres+s3 roundtrip" sh -c "curl -fsS -X POST '$BASE/v1/production/persistence/roundtrip' -H 'content-type: application/json' -d '{\"note\":\"phase8\"}' | grep -q '\"ok\":true'"
check "golden path" sh -c "curl -fsS -X POST '$BASE/v1/golden-path/runs' -H 'content-type: application/json' -d '{}' | grep -q range_id"
check "object storage smoke" sh -c "curl -fsS -X POST '$BASE/v1/ops/smoke/object-storage' | grep -q '\"ok\"'"
check "inference smoke" sh -c "curl -fsS -X POST '$BASE/v1/ops/smoke/inference' | grep -q '\"ok\"'"
check "director simulate" sh -c "curl -fsS -X POST '$BASE/v1/director/campaign/simulate' | grep -q campaign_id"
check "director inference path" sh -c "curl -fsS -X POST '$BASE/v1/director/analyze' -H 'content-type: application/json' -d '{\"incident_summary\":\"Unauthorized admin API access after deploy; session cookies involved.\"}' | grep -q model_proposal"
new_uuid() { python3 -c 'import uuid; print(uuid.uuid4())'; }
check "scheduler plan" sh -c "curl -fsS -X POST '$BASE/v1/scheduler/plan-preview?range_id=$(new_uuid)&budget_usd=10' | grep -q policy_id"
check "scheduler worker mock" sh -c "curl -fsS -X POST '$BASE/v1/scheduler/worker-benchmark?range_id=$(new_uuid)' | grep -q benchmark"
check "api alias /api/v1" sh -c "curl -fsS '$BASE/api/v1/production/dependencies' | grep -q postgres_durable"

GP=$(curl -fsS -X POST "$BASE/v1/golden-path/runs" -H 'content-type: application/json' -d '{}')
RID=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['range_id'])" "$GP")
if sh -c "curl -fsS '$BASE/v1/ranges/$RID/snapshot' | grep -q golden_path.phase"; then
  echo "[PASS] durable event replay"
  pass=$((pass + 1))
else
  echo "[FAIL] durable event replay"
  fail=$((fail + 1))
fi
if timeout 8 curl -sS -N "$BASE/v1/ranges/$RID/stream?after=0" 2>/dev/null | head -c 120 | grep -q '^data:'; then
  echo "[PASS] sse stream opens"
  pass=$((pass + 1))
else
  echo "[WARN] sse stream (non-fatal; replay passed)"
fi

echo "---"
echo "pass=$pass fail=$fail"
exit "$fail"
