#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:4173}"
if [ ! -d tests/e2e/ui-final/visual-core.spec.ts-snapshots ]; then
  echo "No baselines yet — run: npm run screenshots:m20:update"
  npx playwright test tests/e2e/ui-final/visual-core.spec.ts --project=chromium --update-snapshots
else
  npx playwright test tests/e2e/ui-final/visual-core.spec.ts --project=chromium
fi
