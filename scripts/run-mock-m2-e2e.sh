#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate 2>/dev/null || {
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -q -e "packages/contracts[dev]" -e "packages/events[dev]" -e packages/range-runtime \
    -e packages/range-iac -e packages/vultr-control -e packages/scheduler -e packages/evidence \
    -e packages/policy-check -e "apps/api[dev]"
}
pytest -q apps/api/tests/test_mock_m2_e2e.py
echo "Mock M2 E2E: PASS"
