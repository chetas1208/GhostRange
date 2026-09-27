# ghostrange-control + ghostrange-inference

## Inventory (no secrets in this doc)

| Resource | Type | Purpose |
|----------|------|---------|
| `ghostrange-control` | Cloud Compute Shared CPU | Future Docker host (API, web, Postgres, Redis) |
| `ghostrange-inference` | Serverless Inference | LLM API on demand (hypothesis drafts only) |

## Environment variables

Set in **gitignored** `.env` on your machine / later on the control server:

- `VULTR_INFERENCE_API_KEY` — Serverless Inference subscription key (**never** frontend, **never** git)
- `VULTR_API_KEY` — Vultr **Compute** API token (separate; needed for `RealVultrProvider`)
- `GHOSTRANGE_CONTROL_HOST` — public IPv4 of control VM

See `.env.example` for non-secret defaults.

## Status

- VM: verify with `ssh root@$GHOSTRANGE_CONTROL_HOST` then `hostname` → `ghostrange-control`
- **Do not** install Docker/stack until next milestone step
- **Do not** provision GPU, VKE, managed DB, object storage, or worker fleet yet
