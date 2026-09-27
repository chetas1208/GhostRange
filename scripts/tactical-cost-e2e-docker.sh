#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PW_VERSION="$(node -p "require('playwright/package.json').version" 2>/dev/null || echo "1.63.0")"
IMAGE="mcr.microsoft.com/playwright:v${PW_VERSION}-noble"
BASE="${PLAYWRIGHT_BASE_URL:-http://45-76-248-45.nip.io}"
API="${PLAYWRIGHT_API_URL:-$BASE}"

cd "$ROOT"
docker run --rm --init --network host \
  -e PLAYWRIGHT_BASE_URL="$BASE" \
  -e PLAYWRIGHT_API_URL="$API" \
  -v "$ROOT:/work" -w /work \
  "$IMAGE" \
  npx playwright test -c playwright.tactical.config.ts tests/e2e/tactical/tactical-cost.spec.ts --project=chromium
