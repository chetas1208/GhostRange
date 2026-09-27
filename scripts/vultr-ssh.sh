#!/usr/bin/env bash
# SSH to ghostrange-control using repo key: vultr + vultr.pub (see .env).
# Usage: ./scripts/vultr-ssh.sh [remote command...]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env"
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }
# shellcheck disable=SC1090
source "$ENV_FILE"

HOST="${GHOSTRANGE_CONTROL_HOST:?}"
USER="${GHOSTRANGE_CONTROL_SSH_USER:-root}"
KEY="${GHOSTRANGE_CONTROL_SSH_KEY:-${ROOT}/vultr}"
[[ -f "$KEY" ]] || { echo "Missing SSH key: $KEY" >&2; exit 1; }

if [[ $# -eq 0 ]]; then
  exec ssh -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new "${USER}@${HOST}"
fi

export PYTHONPATH="${ROOT}/scripts${PYTHONPATH:+:$PYTHONPATH}"
exec python3 - "$@" <<'PY'
import sys
from vultr_connect import connect

cmd = " ".join(sys.argv[1:])
client = connect()
_, stdout, stderr = client.exec_command(cmd)
out, err = stdout.read().decode(), stderr.read().decode()
if out:
    sys.stdout.write(out)
if err:
    sys.stderr.write(err)
client.close()
PY
