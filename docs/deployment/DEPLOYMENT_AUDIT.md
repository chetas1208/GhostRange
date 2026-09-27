# GhostRange deployment audit (2026-09-26)

## FRONTEND

- **Stack:** Vite 5 + React 18 + R3F (`apps/web`, workspace `packages/ui-3d`)
- **Build:** `npm run build -w apps/web`
- **Prod API URL:** `VITE_API_BASE` empty → same-origin via Caddy (`apps/web/src/config/apiBase.ts`)

## BACKEND

- **Stack:** FastAPI + uvicorn (`apps/api/ghostrange_api/main.py`)
- **CLI:** `ghostrange-api`
- **Routes:** `/v1/*`, `/health`, `/health/live`, `/health/ready`, `/v1/ops/smoke/*`

## AGENTS / WORKERS

- No separate long-running agent containers required for initial production.
- Golden path + M2 orchestrator run inside the API process.

## DATABASE

- **Engine:** PostgreSQL via `PostgresEventStore` (`packages/events/.../store/postgres.py`)
- **Schema:** `schema.sql` applied by `ensure_schema()` (no Alembic/Prisma)
- **Production:** Vultr Managed PostgreSQL only (no Postgres in `docker-compose.prod.yml`)

## MIGRATIONS

- Idempotent DDL via `ensure_schema()` on API startup when `POSTGRES_DSN` + `REDIS_URL` set.

## QUEUE / LIVE EVENTS

- **Redis/Valkey** pub/sub (`RedisBus`) + `EventGateway` when durable mode enabled.
- **Production:** single Valkey container on VM (internal network only).

## OBJECT STORAGE

- **Adapter:** `VultrObjectStorageStore` (boto3 S3-compatible) in `packages/evidence/.../object_store.py`
- **Env:** `OBJECT_STORAGE_PROVIDER=vultr`, `S3_*`

## INFERENCE

- **Integration:** httpx → `VULTR_INFERENCE_BASE_URL/chat/completions` (`ops_routes.inference_smoke`)
- **Key:** `VULTR_INFERENCE_API_KEY` (server-side only)

## EVENT TRANSPORT

- SSE: `GET /v1/ranges/{id}/stream` (Caddy `flush_interval -1`)

## PORTS (production compose)

| Service | Published |
|---------|-----------|
| proxy | 80, 443 |
| api | internal 8000 |
| web | internal 8080 |
| valkey | internal 6379 |

## HEALTH CHECKS

- `/health/live` — process up
- `/health/ready` — Postgres, Redis, optional S3/inference checks
- `/health/version` — deploy SHA

## EXISTING DOCKER SUPPORT

- `docker-compose.dev.yml` — local Postgres + Valkey
- **Added:** `docker-compose.prod.yml`, `deploy/docker/Dockerfile.{api,web}`, `deploy/caddy/Caddyfile`

## MISSING / BLOCKERS (pre-GO)

1. **Managed PostgreSQL** credentials on VM (`.env.production`); local `.env` still points at `localhost`.
2. **Object Storage** subscription + private bucket + keys in `.env.production`.
3. **`VULTR_API_KEY`** not set — no automated provisioning (`ALLOW_VULTR_PROVISION` not enabled).
4. **Remote verification** (smoke, E2E, reboot) pending filled production env.
5. **Agent 24:** **NO-GO** until above verified on `45.76.248.45`.
