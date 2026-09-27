#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8011}"
WEB_PORT="${WEB_PORT:-4173}"
if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
  API_PORT=$((API_PORT + 1))
fi
export VITE_API_BASE="http://127.0.0.1:${API_PORT}"
export VITE_DATA_SOURCE=live
export VITE_GHOSTRANGE_TEST_HOOK=true
export PLAYWRIGHT_BASE_URL="http://127.0.0.1:${WEB_PORT}"
export GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

if [ -x .venv/bin/python3 ]; then
  # Reuse host venv (required for Python 3.11+ inside Playwright Jammy container).
  :
else
  make install-py
fi
if ! npm ci 2>/dev/null; then npm install; fi
npm run typecheck

echo "Building production web (live + test hook)…"
VITE_API_BASE="$VITE_API_BASE" VITE_DATA_SOURCE=live VITE_GHOSTRANGE_TEST_HOOK=true npm run build -w apps/web

source .venv/bin/activate
API_PID=""
WEB_PID=""
cleanup() {
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$WEB_PID" ]] && kill "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT

export GHOSTRANGE_API_HOST=127.0.0.1
export GHOSTRANGE_API_PORT="$API_PORT"
export GHOSTRANGE_CORS_ORIGINS="http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}"
ghostrange-api &
API_PID=$!
for i in $(seq 1 60); do
  curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1 && break
  sleep 0.5
done

npm run preview -w apps/web -- --host 127.0.0.1 --port "$WEB_PORT" &
WEB_PID=$!
for i in $(seq 1 60); do
  curl -sf "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1 && break
  sleep 0.5
done

npx playwright install chromium
node scripts/m20-ui-fixture-audit.mjs
bash scripts/m20-ui-e2e.sh
bash scripts/m20-ui-visual-regression.sh
node scripts/capture-m20-ui.mjs
node scripts/m20-ui-screenshot-index.mjs
node scripts/collect-m20-ui-perf.mjs || echo "perf collection skipped (browser deps)"

echo "M20 UI acceptance pipeline finished."
