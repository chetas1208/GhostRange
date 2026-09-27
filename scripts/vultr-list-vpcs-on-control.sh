#!/usr/bin/env bash
# Run ON ghostrange-control after VULTR_API_KEY ACL includes this host's public IP.
set -eu
cd /opt/ghostrange
set -a
# shellcheck disable=SC1091
source .env.production
set +a
if [[ -z "${VULTR_API_KEY:-}" ]]; then
  echo "VULTR_API_KEY missing in .env.production"
  exit 1
fi
echo "== GET /v2/vpcs =="
curl -sS "https://api.vultr.com/v2/vpcs" -H "Authorization: Bearer ${VULTR_API_KEY}" | python3 -m json.tool
echo
echo "Pick id from vpcs[].id and set GHOSTRANGE_WORKER_VPC_ID in .env.production"
