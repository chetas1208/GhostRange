#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Load SSH deploy target vars only — never source full .env (may contain unquoted secrets).
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^(GHOSTRANGE_CONTROL_|GHOSTRANGE_REMOTE_)' .env | grep -v '_PASSWORD=' || true)
  set +a
fi

HOST="${GHOSTRANGE_CONTROL_HOST:-}"
USER="${GHOSTRANGE_CONTROL_SSH_USER:-root}"
KEY="${GHOSTRANGE_CONTROL_SSH_KEY:-$ROOT/vultr}"
REMOTE_DIR="${GHOSTRANGE_REMOTE_DIR:-/opt/ghostrange}"
SSH_OPTS=(-i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)
SHA="$(git rev-parse --short HEAD 2>/dev/null || echo local)"

if [[ -z "$HOST" ]]; then
  echo "Set GHOSTRANGE_CONTROL_HOST in .env"
  exit 1
fi

export GHOSTRANGE_DEPLOY_SHA="$SHA"
echo "Deploying commit $SHA to $USER@$HOST:$REMOTE_DIR"

RSYNC_EXCLUDES=(
  --exclude .git
  --exclude node_modules
  --exclude .venv
  --exclude __pycache__
  --exclude .pytest_cache
  --exclude .env
  --exclude .env.production
  --exclude 'ranges/**/artifacts'
)

rsync -az --delete -e "ssh ${SSH_OPTS[*]}" "${RSYNC_EXCLUDES[@]}" "$ROOT/" "$USER@$HOST:$REMOTE_DIR/"

REMOTE="
set -euo pipefail
cd $REMOTE_DIR
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi
export GHOSTRANGE_DEPLOY_SHA=$SHA
if [[ ! -f .env.production ]]; then
  echo 'Missing .env.production on VM — copy from .env.production.example and fill Managed PG + Object Storage'
  exit 1
fi
bash scripts/deploy-preflight.sh .env.production
docker compose -f docker-compose.prod.yml build --progress=plain
docker compose -f docker-compose.prod.yml up -d
sleep 8
bash scripts/smoke-test-production.sh http://127.0.0.1
"

ssh "${SSH_OPTS[@]}" "$USER@$HOST" "$REMOTE"

echo "Remote deploy finished. Public smoke: bash scripts/smoke-test-production.sh http://$HOST"
