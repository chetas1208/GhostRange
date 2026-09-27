#!/usr/bin/env bash
# M20 one-command golden campaign. Live requires explicit flags (no interactive prompt).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${GHOSTRANGE_PUBLIC_URL:-http://127.0.0.1:8000}"
BASE="${BASE%/}"
LIVE="${ALLOW_M20_LIVE_CAMPAIGN:-false}"
MAX_USD="${M20_LIVE_CAMPAIGN_MAX_USD:-15}"

echo "M20 golden campaign"
echo "  endpoint: $BASE/v1/campaigns/golden"
echo "  ALLOW_M20_LIVE_CAMPAIGN=$LIVE"
echo "  M20_LIVE_CAMPAIGN_MAX_USD=$MAX_USD"

if [[ "$LIVE" == "true" ]] || [[ "$LIVE" == "1" ]]; then
  echo "  projected live spend cap (env): \$${MAX_USD} — ensure GHOSTRANGE_LIVE + Vultr ACL + VPC"
  export ALLOW_M20_LIVE_CAMPAIGN=true
fi

resp=$(curl -fsS -X POST "$BASE/v1/campaigns/golden" -H 'content-type: application/json' -d '{}')
echo "$resp" | python3 -m json.tool

owned=$(echo "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('owned_workers',[]))")
arena=$(echo "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('arena_recommendation',''))")
phase=$(echo "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin)['campaign'].get('phase',''))")

echo "---"
echo "campaign_phase=$phase arena=$arena owned_workers=$owned"
if [[ "$owned" != "[]" ]]; then
  echo "FAIL: owned_workers not empty"
  exit 1
fi
echo "OK"
