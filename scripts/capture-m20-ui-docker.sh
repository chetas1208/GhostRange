#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright:v1.63.0-jammy}"
docker run --rm --network host \
  -v "$ROOT:/work" -w /work \
  -e PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:4173/}" \
  -e VITE_API_BASE="${VITE_API_BASE:-http://127.0.0.1:8000}" \
  "$IMAGE" \
  bash -lc 'npm ci && node scripts/capture-m20-ui.mjs'
