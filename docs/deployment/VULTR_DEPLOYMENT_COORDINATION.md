# Vultr deployment coordination (24 specialists)

Lead agent integrates; status as of 2026-09-26.

| Agent | Mission | Status | Owned paths | Blockers | Deliverables | Review | Deploy |
|-------|---------|--------|-------------|----------|--------------|--------|--------|
| 01 Auditor | Repo architecture audit | done | docs/deployment/DEPLOYMENT_AUDIT.md | — | audit doc | ok | n/a |
| 02 Frontend container | Prod web image | done | deploy/docker/Dockerfile.web, apps/web/nginx.conf | — | image | ok | pending |
| 03 Backend container | Prod API image | done | deploy/docker/Dockerfile.api | — | image | ok | pending |
| 04 Agent runtime | Separate agent processes | done | — (none required) | — | decision | ok | n/a |
| 05 Compose | docker-compose.prod.yml | done | docker-compose.prod.yml | — | compose | ok | pending |
| 06 Managed Postgres | Vultr PG + TLS | blocked | .env.production.example | no VM credentials | config template | — | no |
| 07 Migrations | ensure_schema | done | packages/events/.../postgres.py | needs live PG | auto on connect | — | no |
| 08 Object storage | S3 integration | blocked | ops_routes, config | no bucket keys | smoke route | — | no |
| 09 Inference | Serverless smoke | partial | ops_routes.py | model id unverified live | smoke route | — | no |
| 10 Network/VPC | VM→PG private/trusted | pending | docs/deployment/VULTR_DEPLOYMENT.md | user console | runbook | — | no |
| 11 Firewall | 22/80/443 only | pending | — | not applied on VM | rules doc | — | no |
| 12 Reverse proxy | Caddy single origin | done | deploy/caddy/Caddyfile | — | proxy | ok | pending |
| 13 Secrets | .env.production | done | .env.production.example | VM file missing | example | ok | no |
| 14 VM hardening | deploy user, docker | in_progress | scripts/deploy-vultr.sh | root-only SSH | install docker | — | partial |
| 15 Event stream | SSE via proxy | done | Caddyfile flush | remote test | config | — | pending |
| 16 Backup | S3 prefixes | done | .env.production.example | — | prefixes | ok | n/a |
| 17 Health | live/ready/version | done | health_routes.py | — | endpoints | ok | pending |
| 18 Deploy automation | scripts/* | done | scripts/deploy-*.sh | preflight needs PG/S3 | scripts | ok | partial |
| 19 Rollback | rollback-vultr.sh | done | scripts/rollback-vultr.sh | — | script | ok | n/a |
| 20 Smoke tests | smoke-test-production.sh | done | scripts/smoke-test-production.sh | blocked on env | script | — | no |
| 21 Browser E2E | Frontend vs prod API | pending | — | no GO stack | — | — | no |
| 22 Security red team | Secret/port scan | pending | — | post-deploy | — | — | no |
| 23 Operations doc | Runbook | done | docs/deployment/VULTR_RUNBOOK.md | — | runbook | ok | n/a |
| 24 Release reviewer | GO/NO-GO | **NO-GO** | docs/deployment/VULTR_DEPLOYMENT_FINAL.md | PG+S3+remote smoke | verdict | — | **NO-GO** |
