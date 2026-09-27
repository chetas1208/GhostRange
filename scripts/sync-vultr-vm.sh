#!/usr/bin/env bash
# Sync repository to ghostrange-control when sshpass/keys are unavailable.
# Uses paramiko (pip install paramiko).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/sync_vultr_vm.py"
