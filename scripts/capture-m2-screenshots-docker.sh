#!/usr/bin/env bash
# Capture §38 UI screenshots using Playwright Docker (avoids host libasound).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/artifacts/screenshots/m2"
PW_VERSION="$(node -p "require('playwright/package.json').version" 2>/dev/null || echo "1.49.0")"
IMAGE="mcr.microsoft.com/playwright:v${PW_VERSION}-noble"
FIXTURE="${VITE_FIXTURE:-m2}"

mkdir -p "$OUT"
cd "$ROOT"

# Kill stale preview servers on common ports
for p in 4173 4174 4175; do
  fuser -k "${p}/tcp" 2>/dev/null || true
done

VITE_FIXTURE="$FIXTURE" npm run build -w apps/web

PREVIEW_PORT=4173
npm run preview -w apps/web -- --host 127.0.0.1 --port "$PREVIEW_PORT" &
PREVIEW_PID=$!

URL="http://127.0.0.1:${PREVIEW_PORT}/"
for _ in $(seq 1 40); do
  if curl -sf -o /dev/null "$URL"; then
    break
  fi
  sleep 0.5
done
if ! curl -sf -o /dev/null "$URL"; then
  echo "Preview server did not become ready at $URL"
  kill "$PREVIEW_PID" 2>/dev/null || true
  exit 1
fi
sleep 1

docker run --rm --init --ipc=host --network host \
  --cgroupns=host \
  -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
  -v "$ROOT:/work" -w /work \
  "$IMAGE" \
  node scripts/capture-ui-snapshots.mjs "$URL" "$OUT" || {
    echo "Docker capture failed; try: sudo apt-get install -y libasound2 && node scripts/capture-ui-snapshots.mjs $URL $OUT"
    kill "$PREVIEW_PID" 2>/dev/null || true
    exit 1
  }

kill "$PREVIEW_PID" 2>/dev/null || true
echo "Screenshots written to $OUT (fixture=$FIXTURE)"
