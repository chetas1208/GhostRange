# Vultr deployment final report — Agent 24 verdict

**Decision: NO-GO** (2026-09-26)

## WHAT IS DEPLOYED?

Production **artifacts** are in the repository (Dockerfiles, compose, Caddy, scripts, API wiring). On **`ghostrange-control`**: Docker Engine is installed, source is at `/opt/ghostrange`, and **`ghostrange-api:deploy-test`** / **`ghostrange-web:deploy-test`** images built successfully. The **stack is not running** because `/opt/ghostrange/.env.production` (Managed PostgreSQL + Object Storage) is missing.

## WHAT COMMIT IS DEPLOYED?

Not pinned on VM until `bash scripts/deploy-vultr.sh` completes with `.env.production` present. Local tree: run `git rev-parse HEAD` after first commit.

## WHAT URL/IP SERVES THE FRONTEND?

Target: `http://45.76.248.45/` (Caddy → web). **Not confirmed** post-smoke.

## HOW DOES THE FRONTEND REACH THE BACKEND?

Same origin: Caddy routes `/v1/*` and `/health*` to API; static UI on `/`.

## WHICH CONTAINERS ARE RUNNING?

Expected after deploy: `proxy`, `web`, `api`, `valkey`. **Not verified remotely.**

## AGENT PROCESSES

None separate; orchestration inside `api`.

## WHERE IS POSTGRESQL?

**Required:** Vultr Managed PostgreSQL. **Not connected** (operator `.env` still had localhost DSN).

## IS POSTGRESQL PUBLICLY ACCESSIBLE?

Unknown until instance exists; must be restricted via Trusted Sources or VPC.

## TLS FOR DATABASE?

Configured via DSN / optional CA path in runbook.

## MIGRATIONS

`ensure_schema()` on API connect — **not run against managed PG yet.**

## ARTIFACTS / OBJECT STORAGE

Adapter ready; **no bucket configured** in environment.

## BUCKET PRIVATE / VERSIONING?

Must be set in Vultr console when created.

## S3 ROUNDTRIP / INFERENCE SMOKE

Implemented at `/v1/ops/smoke/*` — **not executed successfully in production.**

## PUBLIC PORTS

Target: 22, 80, 443. Firewall hardening **pending.**

## SECRETS

Template only (`.env.production.example`); inference key in local gitignored `.env` only.

## FRONTEND SECRET SCAN

Not run on deployed bundle (no prod build deployed).

## E2E / SSE / REBOOT TESTS

**Not run.**

## ROLLBACK

`scripts/rollback-vultr.sh` exists.

## RESOURCE INVENTORY

| Resource | Count |
|----------|-------|
| ghostrange-control VM | 1 |
| Managed PostgreSQL | 0 connected (provision required) |
| Object Storage + bucket | 0 connected |
| Serverless Inference | 1 subscription (key in local `.env`) |
| GPU / K8s / LB | 0 |

## WHAT REMAINS MOCKED?

Golden path default `GHOSTRANGE_LIVE_PROVIDER=mock`; M11–M14 simulation paths unchanged.

## WHAT FAILED?

Missing production `POSTGRES_DSN` (non-localhost), S3 credentials on VM, remote smoke/E2E/reboot, firewall verification.

## AGENT 24 DECISION

**NO-GO** — automatic conditions: managed PG not in use, artifact roundtrip not proven remotely, health/smoke not passed on public IP, reboot test not done.

## NEXT OPERATOR STEPS (minimum)

1. Create Managed PostgreSQL + Object Storage per `VULTR_DEPLOYMENT.md`.
2. Write `/opt/ghostrange/.env.production` on the VM (chmod 600).
3. Run `bash scripts/deploy-vultr.sh`.
4. Run public smoke: `bash scripts/smoke-test-production.sh http://45.76.248.45`.
5. Re-run Agent 24 checklist; update this file to **GO** only after all pass.
