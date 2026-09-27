#!/usr/bin/env bash
# On ghostrange-control: list VPCs in worker region or create ghostrange-worker-vpc.
set -eu
REGION="${VULTR_WORKER_REGION:-lax}"
cd /opt/ghostrange
set -a
# shellcheck disable=SC1091
source .env.production
set +a
test -n "${VULTR_API_KEY:-}"

list() {
  curl -sS "https://api.vultr.com/v2/vpcs" -H "Authorization: Bearer ${VULTR_API_KEY}"
}

resp=$(list)
if echo "$resp" | grep -q 'Unauthorized IP'; then
  echo "FAIL: Vultr API key IP ACL must include this host public IP (45.76.248.45/32)."
  echo "$resp"
  exit 1
fi

id=$(echo "$resp" | python3 -c "
import json,sys,os
d=json.load(sys.stdin)
region=os.environ.get('REGION','lax')
for v in d.get('vpcs',[]):
    if v.get('region')==region:
        print(v['id']); break
" REGION="$REGION")

if [[ -z "${id:-}" ]]; then
  echo "Creating VPC in region $REGION ..."
  create=$(curl -sS -X POST "https://api.vultr.com/v2/vpcs" \
    -H "Authorization: Bearer ${VULTR_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"region\":\"${REGION}\",\"description\":\"ghostrange-worker-vpc\",\"v4_subnet\":\"10.99.0.0\",\"v4_subnet_mask\":16}")
  id=$(echo "$create" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('vpc',{}).get('id',''))")
fi

if [[ -z "${id:-}" ]]; then
  echo "Could not resolve VPC id"
  exit 1
fi

echo "GHOSTRANGE_WORKER_VPC_ID=${id}"
if grep -q '^GHOSTRANGE_WORKER_VPC_ID=' .env.production; then
  sed -i "s|^GHOSTRANGE_WORKER_VPC_ID=.*|GHOSTRANGE_WORKER_VPC_ID=${id}|" .env.production
else
  echo "GHOSTRANGE_WORKER_VPC_ID=${id}" >> .env.production
fi
chmod 600 .env.production
echo "Updated .env.production"
