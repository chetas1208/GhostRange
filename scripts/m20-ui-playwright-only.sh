#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-$(cat /tmp/ghostrange-ui-web.url 2>/dev/null || echo http://127.0.0.1:4173)}"
export VITE_API_BASE="${VITE_API_BASE:-http://127.0.0.1:8011}"
npx playwright install chromium
node scripts/m20-ui-fixture-audit.mjs
bash scripts/m20-ui-e2e.sh
bash scripts/m20-ui-visual-regression.sh
node scripts/capture-m20-ui.mjs
node scripts/m20-ui-screenshot-index.mjs
node scripts/collect-m20-ui-perf.mjs || true
