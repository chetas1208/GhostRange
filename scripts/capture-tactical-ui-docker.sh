#!/usr/bin/env bash
# Capture 12 tactical PNGs via Playwright Docker (no host libasound).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PW_VERSION="$(node -p "require('playwright/package.json').version" 2>/dev/null || echo "1.63.0")"
IMAGE="mcr.microsoft.com/playwright:v${PW_VERSION}-noble"
BASE="${BASE_URL:-http://45-76-248-45.nip.io}"
API="${API_URL:-$BASE}"

cd "$ROOT"
mkdir -p artifacts/screenshots/tactical

docker run --rm --init --network host \
  -e BASE_URL="$BASE" \
  -e API_URL="$API" \
  -v "$ROOT:/work" -w /work \
  "$IMAGE" \
  node scripts/capture-tactical-ui.mjs

echo "Tactical screenshots: $ROOT/artifacts/screenshots/tactical"
