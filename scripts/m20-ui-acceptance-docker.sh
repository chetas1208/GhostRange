#!/usr/bin/env bash
# Host starts API/preview; Playwright runs in pinned Jammy image (--network host).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright:v1.63.0-jammy}"

bash scripts/m20-ui-acceptance-services.sh
PLAYWRIGHT_BASE_URL="$(cat /tmp/ghostrange-ui-web.url)"
trap 'kill $(cat /tmp/ghostrange-ui-api.pid 2>/dev/null) 2>/dev/null; kill $(cat /tmp/ghostrange-ui-web.pid 2>/dev/null) 2>/dev/null; fuser -k 4173/tcp 8011/tcp 2>/dev/null || true' EXIT

docker run --rm --network host \
  -v "$ROOT:/work" -w /work \
  -e PLAYWRIGHT_BASE_URL="$PLAYWRIGHT_BASE_URL" \
  -e VITE_API_BASE="${VITE_API_BASE:-http://127.0.0.1:8011}" \
  "$IMAGE" \
  bash -lc 'npm install && bash scripts/m20-ui-playwright-only.sh'

echo "Docker UI acceptance finished."
