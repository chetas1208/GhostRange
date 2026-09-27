# One live Vultr worker (GhostScheduler)

## 1. VM env (`/opt/ghostrange/.env.production`, chmod 600)

```bash
VULTR_API_KEY=...          # Compute API token (not inference key)
GHOSTSCHEDULER_LIVE=true
GHOSTRANGE_WORKER_VPC_ID=... # existing VPC for attach_vpc
MAX_ACTIVE_WORKERS=1
MAX_ACTIVE_WORLDS=1
```

Restart: `cd /opt/ghostrange && docker compose -f docker-compose.prod.yml up -d`

## 2. Read-only auth check

```bash
curl -s http://127.0.0.1/v1/scheduler/guardrails | jq .
curl -s http://127.0.0.1/v1/scheduler/compute-dry-check | jq .
```

Expect `owned_worker_count: 0` before first run.

## 3. One billable benchmark

```bash
bash scripts/live-worker-lifecycle.sh http://127.0.0.1
```

Or from your laptop (after guardrails OK):

```bash
bash scripts/live-worker-lifecycle.sh http://45.76.248.45
```

## 4. Verify teardown

- `compute-dry-check` → `owned_worker_count: 0`
- Vultr console → no ghostrange-tagged worker instance
- Postgres → row in `scheduler_worker_runs` with `status: terminated`
- Object Storage → evidence blob for `run_id` (via API response `evidence_artifact_id`)

## Next code milestone

Replace live `run_benchmark` stub with cloud-init + worker agent (register, pull task, upload artifact, drain).
