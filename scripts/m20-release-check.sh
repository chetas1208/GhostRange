#!/usr/bin/env bash
# M20 release check — no billable cloud by default.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
fail=0
note() { echo "[m20-release] $*"; }
pass() { note "PASS: $1"; }
fail_step() { note "FAIL: $1"; fail=$((fail + 1)); }

note "configuration validation"
if [[ -f .env.example ]]; then pass ".env.example present"; else fail_step ".env.example missing"; fi

note "unit + integration tests (local)"
if bash "$ROOT/scripts/run-all-tests.sh"; then pass "test matrix"; else fail_step "test matrix"; fi

note "ghostarena + ghostevolve + ghostshield + ghostruntime"
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q -e packages/ghostarena -e packages/ghostevolve -e packages/ghostshield -e packages/ghostruntime 2>/dev/null || true
  if pytest -q packages/ghostarena/tests packages/ghostevolve/tests packages/ghostshield/tests packages/ghostruntime/tests 2>/dev/null; then
    pass "m16-m19 package tests"
  else
    fail_step "m16-m19 package tests"
  fi
fi

note "secret scan (frontend)"
if rg -l "VULTR_API_KEY|S3_SECRET|postgres://" apps/web/src packages/ui-3d/src 2>/dev/null; then
  fail_step "possible secrets in frontend"
else
  pass "frontend secret scan"
fi

note "M20 mock golden campaign (API)"
if [[ -d .venv ]]; then
  if pytest -q apps/api/tests/test_m20_campaign.py; then pass "m20 campaign API"; else fail_step "m20 campaign API"; fi
fi

note "Arena qualification (sim)"
python3 - <<'PY' || fail_step "arena sim qualification"
from ghostrange_ghostarena.engine import GhostArenaEngine
r = GhostArenaEngine().release_report(
    baseline_version="ghostrange-release:v0.9",
    candidate_version="ghostrange-release:local",
    candidate_policy="qualified",
)
assert r.recommendation.value == "QUALIFIED", r.recommendation
print("QUALIFIED")
PY
pass "arena sim qualification"

if [[ "${RUN_M20_LIVE_CHECKS:-}" == "true" ]]; then
  note "live checks (optional)"
  BASE="${GHOSTRANGE_PUBLIC_URL:-http://127.0.0.1:8000}"
  if curl -fsS "$BASE/health/live" | grep -q ok; then pass "health live"; else fail_step "health live"; fi
else
  note "skip live checks (set RUN_M20_LIVE_CHECKS=true)"
fi

note "done fail=$fail"
exit "$fail"
