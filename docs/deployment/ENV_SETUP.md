# Environment files (recommended layout)

## Two files, two places

| File | Where | Purpose |
|------|--------|---------|
| **`.env`** | Your laptop (gitignored) | SSH to VM, inference key, optional local dev overrides |
| **`.env.production`** | **`/opt/ghostrange/.env.production`** on `ghostrange-control` only (chmod **600**) | Everything the Docker stack needs at runtime |

Never commit either file. Never put storage or DB secrets in `VITE_*`.

## Production variables (VM)

Copy from `.env.production.example`, then set:

- **`POSTGRES_DSN`** — Vultr connection string as **`postgresql://...`** (not `postgres://`), with **`?sslmode=require`**
- **`REDIS_URL`** — `redis://valkey:6379/0` (compose overrides this for the api service)
- **`OBJECT_STORAGE_PROVIDER=vultr`**
- **`S3_ENDPOINT`** — `https://<region>.vultrobjects.com` (e.g. `sjc1`)
- **`S3_ACCESS_KEY_ID`**, **`S3_SECRET_ACCESS_KEY`**, **`S3_BUCKET`**, **`S3_REGION`**
- **`VULTR_INFERENCE_API_KEY`** — Serverless Inference only

## Deploy after env is set

```bash
bash scripts/sync-vultr-vm.sh
# upload .env.production separately (deploy-vultr.sh does both when SSH works)
ssh root@45.76.248.45 'chmod 600 /opt/ghostrange/.env.production'
cd /opt/ghostrange && bash scripts/deploy-preflight.sh .env.production
docker compose -f docker-compose.prod.yml up -d --build
bash scripts/smoke-test-production.sh http://127.0.0.1
bash scripts/smoke-test-production.sh http://45.76.248.45
```

## Bucket

Create a **private** bucket in the Object Storage subscription (versioning ON). This deployment uses **`ghostrange-artifacts-hack26`** if no bucket existed yet.
