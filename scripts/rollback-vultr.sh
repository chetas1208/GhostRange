#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PREV="${1:-}"
if [[ -z "$PREV" ]]; then
  echo "Usage: $0 <previous-git-sha>"
  exit 1
fi
export GHOSTRANGE_DEPLOY_SHA="$PREV"
docker compose -f docker-compose.prod.yml pull 2>/dev/null || true
docker compose -f docker-compose.prod.yml up -d --build
echo "rollback: deployed image tag $PREV"
