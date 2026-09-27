# GhostRange on Vultr — architecture

## Compute

- **VM:** `ghostrange-control` — `45.76.248.45` (Ubuntu 26.04, ~4 vCPU / 7 GiB RAM)
- **Deploy root:** `/opt/ghostrange`

## Docker services (production)

```text
Internet :80/:443
    → Caddy (proxy)
        → web:8080 (nginx + Vite static)
        → api:8000 (FastAPI)
    → valkey:6379 (internal only)
```

## External services

| Service | Role |
|---------|------|
| Vultr Managed PostgreSQL | `event_log`, seq counters (`POSTGRES_DSN`) |
| Vultr Object Storage | Artifact blobs (`S3_*`, private bucket) |
| Vultr Serverless Inference | `VULTR_INFERENCE_*` (API only) |

## Data flow

- Events: API → Postgres append → Redis publish → SSE clients
- Artifacts: API → `VultrObjectStorageStore` (content-addressed keys under `artifacts/`)
- Inference: API → HTTPS chat completions (degraded if unavailable)

## Secret boundaries

- All cloud credentials in `/opt/ghostrange/.env.production` (chmod 600)
- Frontend build: no `VITE_*` secrets; `VITE_API_BASE` empty in prod

## Backup

- Optional logical PG dump → Object Storage prefix `backups/` (operator-driven)
