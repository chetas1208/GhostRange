#!/usr/bin/env bash
# Copy server-side secrets from .env into .env.production (never prints values).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV="$ROOT/.env"
PROD="$ROOT/.env.production"
test -f "$ENV" && test -f "$PROD"

copy_if_set() {
  local key=$1
  local val
  val=$(grep -E "^${key}=" "$ENV" 2>/dev/null | tail -1 | cut -d= -f2- || true)
  if [[ -z "$val" ]]; then
    return 0
  fi
  python3 - "$key" "$val" "$PROD" <<'PY'
import sys
key, val, path = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().splitlines()
out, seen = [], False
for line in lines:
    if line.startswith(f"{key}=") or line.startswith(f"# {key}="):
        out.append(f"{key}={val}")
        seen = True
    else:
        out.append(line)
if not seen:
    out.append(f"{key}={val}")
open(path, "w").write("\n".join(out) + "\n")
PY
  echo "merged $key"
}

for key in VULTR_API_KEY GHOSTRANGE_WORKER_VPC_ID GHOSTSCHEDULER_LIVE \
  VULTR_WORKER_REGION VULTR_WORKER_PLAN VULTR_WORKER_OS_ID; do
  copy_if_set "$key"
done

echo "Done. Review $PROD then: bash scripts/sync-vultr-vm.sh (or upload .env.production to VM)."
