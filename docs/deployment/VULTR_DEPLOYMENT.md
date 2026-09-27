# Deploy GhostRange to ghostrange-control

## Prerequisites

1. VM SSH access (`GHOSTRANGE_CONTROL_HOST`, user, key or password in gitignored `.env`).
2. **One** Vultr Managed PostgreSQL (same region as VM preferred).
3. **One** Object Storage subscription + **private** bucket (versioning ON).
4. Existing Serverless Inference key (`VULTR_INFERENCE_API_KEY`).
5. On VM: `/opt/ghostrange/.env.production` from `.env.production.example`.

### Managed PostgreSQL (console)

1. Products → Databases → Deploy PostgreSQL.
2. Region: match `ghostrange-control`.
3. Trusted Sources: **only** `45.76.248.45/32` (or attach VM + DB to same VPC).
4. Copy connection string; use Vultr port and `sslmode=require`.
5. Optional: download CA cert → `/opt/ghostrange/secrets/vultr-postgres-ca.pem`.

### Object Storage (console)

1. Products → Object Storage → Add subscription.
2. Create bucket `ghostrange-artifacts-<unique>`; **private**; versioning **ON**.
3. Copy S3 endpoint, access key, secret key into `.env.production`.

### Automated provisioning

Only when `ALLOW_VULTR_PROVISION=true` **and** `VULTR_API_KEY` is set (not configured in this repo yet).

## Deploy from dev machine

```bash
# Fill VM .env.production first (SSH once):
# scp .env.production root@45.76.248.45:/opt/ghostrange/.env.production

bash scripts/deploy-vultr.sh
```

## On-VM manual

```bash
cd /opt/ghostrange
export GHOSTRANGE_DEPLOY_SHA=$(git rev-parse --short HEAD)
bash scripts/deploy-preflight.sh .env.production
docker compose -f docker-compose.prod.yml up -d --build
bash scripts/smoke-test-production.sh http://127.0.0.1
```

## systemd (optional)

```bash
sudo cp deploy/systemd/ghostrange.service /etc/systemd/system/
sudo systemctl enable ghostrange
```

## HTTPS + domain

When `APP_DOMAIN` is available, replace `deploy/caddy/Caddyfile` with automatic HTTPS block for that host and reload proxy.
