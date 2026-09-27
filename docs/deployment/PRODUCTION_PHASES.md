# Production phases — status

## Phases 1–2: Service wiring + stack

- **Done:** `docker compose -f docker-compose.prod.yml up -d` on `45.76.248.45`
- **Env:** gitignored `.env` (dev) + `/opt/ghostrange/.env.production` (VM)
- **Aliases:** `POSTGRES_DSN` or `DATABASE_URL` + `DATABASE_SSLMODE=require`
- **Public URL:** http://45.76.248.45/ (Caddy → web + `/v1/*` + `/api/v1/*`)

## Phase 3: Postgres persistence

- Schema: `packages/events/.../schema.sql` (+ `artifact_registry`, `scheduler_worker_runs`)
- Proof: `POST /v1/production/persistence/roundtrip`
- Golden path events durably stored; `GET /v1/ranges/{id}/snapshot` replays from Vultr PG

## Phase 4: Object Storage

- Metadata in Postgres, bytes in S3 (`artifact_registry` + `VultrObjectStorageStore`)
- Worker benchmark jobs write evidence artifacts to the bucket

## Phase 5: Inference in agent path

- `POST /v1/director/analyze` — inference + deterministic GhostDirector campaign
- Ops smoke: `POST /v1/ops/smoke/inference`
- Model output is advisory; budgets/policy remain server-side

## Phase 6–7: Frontend + proxy

- Same-origin API (`VITE_API_BASE` empty in prod build)
- Caddy: `/`, `/v1/*`, `/api/*` (strip prefix), `/health*`
- HTTPS: add `APP_DOMAIN` and update `deploy/caddy/Caddyfile` when DNS is ready

## Phase 8: Smoke

```bash
bash scripts/production-phase-checklist.sh http://45.76.248.45
```

## Phases 9–15: GhostScheduler → Vultr compute

- **Adapter:** `apps/api/ghostrange_api/compute_provider.py` (`MockComputeProvider` / `VultrComputeProvider`)
- **Job API:** `POST /v1/scheduler/worker-benchmark?range_id=...` (mock by default)
- **Live workers:** set `VULTR_API_KEY`, `GHOSTSCHEDULER_LIVE=true`, `GHOSTRANGE_WORKER_VPC_ID`, plan/region/os env — **creates billable instances**
- **Budgets (env):** `MAX_ACTIVE_WORKERS`, `MAX_ACTIVE_WORLDS`, cost caps, `MAX_WORKER_LIFETIME_MINUTES`

## Not automated here

- **VM reboot test** — run manually during maintenance window
- **Live Vultr worker E2E** — requires Compute API token + VPC id (user-controlled)
