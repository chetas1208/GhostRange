#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
API_PORT="${API_PORT:-8011}"
WEB_PORT="${WEB_PORT:-4173}"
export VITE_API_BASE="http://127.0.0.1:${API_PORT}"
export VITE_DATA_SOURCE=live
export VITE_GHOSTRANGE_TEST_HOOK=true
export PLAYWRIGHT_BASE_URL="http://127.0.0.1:${WEB_PORT}"
echo "$PLAYWRIGHT_BASE_URL" > /tmp/ghostrange-ui-web.url

for port in "$WEB_PORT" "$API_PORT"; do
  pid=$(lsof -ti tcp:"$port" 2>/dev/null | head -1 || true)
  if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || true; fi
done
sleep 0.5

echo "Building production web for acceptance…"
VITE_API_BASE="$VITE_API_BASE" VITE_DATA_SOURCE=live VITE_GHOSTRANGE_TEST_HOOK=true npm run build -w apps/web

source .venv/bin/activate
export GHOSTRANGE_API_HOST=127.0.0.1
export GHOSTRANGE_API_PORT="$API_PORT"
export GHOSTRANGE_CORS_ORIGINS="http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}"
ghostrange-api &
echo $! > /tmp/ghostrange-ui-api.pid
npm run preview -w apps/web -- --host 127.0.0.1 --port "$WEB_PORT" --strictPort &
echo $! > /tmp/ghostrange-ui-web.pid

for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1 && curl -sf "${PLAYWRIGHT_BASE_URL}/" >/dev/null 2>&1; then
    echo "UI acceptance services ready: API ${API_PORT} WEB ${WEB_PORT}"
    exit 0
  fi
  sleep 0.5
done
echo "services failed to become ready" >&2
exit 1
