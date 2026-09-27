#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SHA="${GHOSTRANGE_DEPLOY_SHA:-unknown}"
echo "deploy_sha=$SHA"
docker compose -f docker-compose.prod.yml ps
curl -fsS http://127.0.0.1/health/version 2>/dev/null || echo "proxy/api unreachable"
df -h / | tail -1
