#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${1:-.env.production}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

fail=0
check() { if "$@"; then echo "OK  $*"; else echo "FAIL $*"; fail=1; fi; }
check_set() {
  local label=$1 val=$2
  if [[ -n "$val" ]]; then echo "OK  $label"; else echo "FAIL $label missing"; fail=1; fi
}

check docker info >/dev/null
check docker compose -f docker-compose.prod.yml config >/dev/null
check_set POSTGRES_DSN "${POSTGRES_DSN:-}"
check_set VULTR_INFERENCE_API_KEY "${VULTR_INFERENCE_API_KEY:-}"
if [[ "${OBJECT_STORAGE_PROVIDER:-}" = "vultr" ]]; then echo "OK  OBJECT_STORAGE_PROVIDER=vultr"; else echo "FAIL OBJECT_STORAGE_PROVIDER"; fail=1; fi
check_set S3_ENDPOINT "${S3_ENDPOINT:-}"
check_set S3_BUCKET "${S3_BUCKET:-}"
check_set S3_ACCESS_KEY_ID "${S3_ACCESS_KEY_ID:-}"
check_set S3_SECRET_ACCESS_KEY "${S3_SECRET_ACCESS_KEY:-}"

if [[ "${APP_ENV:-}" = "production" ]] || [[ "${GHOSTRANGE_REQUIRE_DURABLE:-}" =~ ^(1|true|yes)$ ]]; then
  if [[ "${GHOSTRANGE_LIVE:-}" =~ ^(1|true|yes)$ ]]; then echo "OK  GHOSTRANGE_LIVE"; else echo "FAIL GHOSTRANGE_LIVE must be true"; fail=1; fi
  if [[ "${GHOSTRANGE_LIVE_PROVIDER:-}" = "vultr" ]]; then echo "OK  GHOSTRANGE_LIVE_PROVIDER=vultr"; else echo "FAIL GHOSTRANGE_LIVE_PROVIDER must be vultr (no mock)"; fail=1; fi
  check_set VULTR_API_KEY "${VULTR_API_KEY:-}"
  if [[ "${GHOSTSCHEDULER_LIVE:-}" =~ ^(1|true|yes)$ ]]; then echo "OK  GHOSTSCHEDULER_LIVE"; else echo "FAIL GHOSTSCHEDULER_LIVE must be true"; fail=1; fi
  check_set GHOSTRANGE_WORKER_VPC_ID "${GHOSTRANGE_WORKER_VPC_ID:-}"
fi

if command -v python3 >/dev/null; then
  python3 - <<'PY' || fail=1
import os, sys
from urllib.parse import urlparse
dsn=os.environ.get("POSTGRES_DSN","")
if "localhost" in dsn or "127.0.0.1" in dsn:
    print("FAIL POSTGRES_DSN must not point at localhost in production")
    sys.exit(1)
print("OK  POSTGRES_DSN host is external")
PY
fi

avail=$(df -BG . | awk 'NR==2 {gsub(/G/,"",$4); print $4}')
if [[ "${avail:-0}" -lt 5 ]]; then
  echo "WARN disk free ${avail}G — builds may need swap"
fi

exit "$fail"
