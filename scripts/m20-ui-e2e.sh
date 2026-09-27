#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:4173}"
npx playwright test tests/e2e/ui-final/golden-path.spec.ts tests/e2e/ui-final/smoke.spec.ts tests/e2e/ui-final/sse-reconnect.spec.ts tests/e2e/ui-final/keyboard.spec.ts --project=chromium
