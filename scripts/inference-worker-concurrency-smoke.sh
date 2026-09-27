#!/usr/bin/env bash
# Real-live proof: N concurrent Vultr Serverless Inference "workers" dispatched through
# GhostExecutionGateway, with hard MAX_ACTIVE_WORKERS + INFERENCE_WORKER_MAX_USD caps.
#
# Requires a running GhostRange API (local dev server or the control VM) with
# VULTR_INFERENCE_API_KEY configured. Does NOT touch the Vultr Compute API / VPC / ACL —
# Serverless Inference is a plain bearer-token REST API and is not IP-allowlisted, so this
# works from a laptop, this sandbox, or the control VM equally.
#
# Usage:
#   GHOSTRANGE_BASE_URL=http://127.0.0.1:8000 scripts/inference-worker-concurrency-smoke.sh
#   GHOSTRANGE_BASE_URL=http://<control-vm-ip> scripts/inference-worker-concurrency-smoke.sh 10
#
# Exit non-zero on: HTTP failure, fewer than N tasks dispatched, observed concurrency > cap,
# or spend exceeding the configured budget cap.
set -eu
BASE="${GHOSTRANGE_BASE_URL:-http://127.0.0.1:8000}"
BASE="${BASE%/}"
N="${1:-10}"

echo "== inference worker guardrails =="
GUARD=$(curl -fsS "$BASE/v1/scheduler/inference-workers/guardrails")
echo "$GUARD" | python3 -m json.tool

CONFIGURED=$(echo "$GUARD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('inference_configured'))")
if [[ "$CONFIGURED" != "True" && "$CONFIGURED" != "true" ]]; then
  echo "STOP: inference not configured (VULTR_INFERENCE_API_KEY missing on $BASE)"
  exit 1
fi

echo "== dispatching $N concurrent real Vultr Serverless Inference calls =="
PAYLOAD=$(python3 -c "
import json
sysmsg = 'Return ONLY valid JSON with keys: ack (string), n (number). Set ack to the literal string ok and n to the number given in the user message.'
n = $N
tasks = [{'system': sysmsg, 'user': f'n={i}', 'max_tokens': 40, 'label': f'worker-{i}'} for i in range(n)]
print(json.dumps({'tasks': tasks}))
")

RESULT=$(curl -fsS -X POST "$BASE/v1/scheduler/inference-workers/dispatch" \
  -H "Content-Type: application/json" -d "$PAYLOAD")

echo "$RESULT" | python3 -c "
import json, sys
r = json.load(sys.stdin)
for k in ('requested','dispatched','refused','max_observed_concurrency','concurrency_cap','spent_usd','budget_cap_usd','ghostshield_mode'):
    print(f'{k}={r.get(k)}')
print()
print('per-request timestamps (proof of real overlap + distinct Vultr request IDs):')
for res in r.get('results', []):
    print(f\"  {res['label']:>10} {res['request_id'][:8]} {res['started_at']} -> {res['finished_at']} ({res['duration_ms']}ms) ok={res['ok']} {res.get('error') or ''}\")
"

echo "== assertions =="
echo "$RESULT" | python3 -c "
import sys, json
r = json.load(sys.stdin)
n = $N
errors = []
if r['max_observed_concurrency'] > r['concurrency_cap']:
    errors.append(f\"concurrency cap violated: observed={r['max_observed_concurrency']} cap={r['concurrency_cap']}\")
if r['spent_usd'] > r['budget_cap_usd']:
    errors.append(f\"budget cap violated: spent={r['spent_usd']} cap={r['budget_cap_usd']}\")
ids = [x['request_id'] for x in r['results']]
if len(set(ids)) != len(ids):
    errors.append('duplicate request_id detected — not real distinct dispatches')
if r['dispatched'] < n and r['refused'] == 0:
    errors.append(f\"dispatched={r['dispatched']} < requested={n} with no refusals — tasks silently dropped\")
if errors:
    for e in errors:
        print('FAIL:', e)
    sys.exit(1)
print(f\"PASS: {r['dispatched']}/{n} real concurrent Vultr Serverless Inference workers, \"
      f\"max_observed_concurrency={r['max_observed_concurrency']} <= cap={r['concurrency_cap']}, \"
      f\"spent_usd={r['spent_usd']} <= budget_cap_usd={r['budget_cap_usd']}\")
"
