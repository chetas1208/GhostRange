#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1}"
BASE="${BASE%/}"

curl -fsS "$BASE/health/live" | grep -q '"ok"'
curl -fsS "$BASE/health/ready" | grep -q '"ok"'
curl -fsS "$BASE/" | grep -qi '<html'
curl -fsS -X POST "$BASE/v1/golden-path/runs" -H 'content-type: application/json' -d '{}' | grep -q range_id
curl -fsS -X POST "$BASE/v1/ops/smoke/object-storage" | grep -q '"ok"'
curl -fsS -X POST "$BASE/v1/ops/smoke/inference" | grep -q '"ok"'
curl -fsS -X POST "$BASE/v1/production/persistence/roundtrip" \
  -H 'content-type: application/json' -d '{"note":"smoke"}' | grep -q '"ok":true'
curl -fsS -X POST "$BASE/v1/director/campaign/simulate" | grep -q campaign_id
echo "smoke: PASS base=$BASE"
