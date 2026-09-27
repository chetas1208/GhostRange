# Vultr Compute API — IP ACL

If `GET /v2/vpcs` returns:

```json
{"error":"Unauthorized IP address: …","status":401}
```

the **Personal Access Token** is valid but this host’s public IP is not allowlisted.

## Fix (Vultr Customer Portal)

1. [API settings](https://my.vultr.com/settings/#settingsapi)
2. Edit the **Compute** token used as `VULTR_API_KEY`
3. Add **both** (recommended):
   - `45.76.248.45/32` — `ghostrange-control` (where workers are provisioned)
   - Your dev machine public IP (e.g. Cursor runner) if you call the API locally
4. Or disable IP restriction for hackathon-only tokens (rotate after the event)

## Then run (from repo)

```bash
python3 scripts/vultr_ensure_worker_vpc.py
```

Creates or reuses a VPC in `VULTR_WORKER_REGION` (default `lax`), updates `.env`, `.env.production`, and recycles the prod API container.

## Manual VPC id (console)

Network → VPC → create in **lax** → copy UUID:

```bash
python3 scripts/vultr_ensure_worker_vpc.py --sync-id YOUR-UUID-HERE
```

Verify:

```bash
curl -s http://45.76.248.45/v1/scheduler/compute-dry-check | jq .
# expect ok: true, worker_vpc_configured: true
```
