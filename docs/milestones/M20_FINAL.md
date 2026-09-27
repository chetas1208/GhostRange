# M20 Final — GhostRange One

## Agent 59 — claims review (summary)

| Claim | Verdict |
|-------|---------|
| "Autonomous investigation in controlled environments" | PARTIALLY_SUPPORTED |
| "Real Vultr workers in every demo" | UNSUPPORTED (mock default; live gated) |
| "Fully integrated causal + watch + runtime in one campaign" | UNSUPPORTED |
| "Production-ready SOC platform" | OVERSTATED → use RESEARCH_PROTOTYPE |
| "GhostArena qualifies release" | PARTIALLY_SUPPORTED (sim only) |

Unsupported claims removed/softened in README status section.

## Agent 60 decision: **NO-SHIP**

Triggers: no verified live golden path; GhostShield bypass; no runtime restart recovery in campaign; frontend not production-state-driven; no m20 screenshots; git has no baseline commit; full spec golden timeline not satisfied.

---

## What is GhostRange?

Evidence-grounded cyber digital-twin investigation: compile authorized input, hypothesize, experiment, verify, optionally act through GhostShield, audit via GhostLedger, improve via GhostEvolve, qualify via GhostArena.

## Canonical campaign flow

`POST /v1/campaigns/golden` — see `docs/architecture/GHOSTRANGE_FINAL_ARCHITECTURE.md`.

## Golden campaign (mock, verified)

- **Input:** `ranges/.../docker-compose.yml` (machine-readable).
- **Hypotheses:** 3 (middleware, identity cache, gateway routing); hidden true mechanism `session_refresh_cache`.
- **Workers:** 0 in mock path; `owned_workers: []`.
- **Arena:** QUALIFIED (sim).
- **Cost:** $0 mock.

## Live campaign

**NOT_RUN** — requires `ALLOW_M20_LIVE_CAMPAIGN=true`, Vultr ACL, VPC, Postgres worker store.

## Vultr services used (when configured)

| Service | Role |
|---------|------|
| Cloud Compute | Control VM + ephemeral workers |
| Managed PostgreSQL | Events, worker leases |
| Object Storage | Artifacts |
| Serverless Inference | Director/analyze smoke; **+ real concurrent worker pool** (`inference_worker_pool.py`, `/v1/scheduler/inference-workers/dispatch`) — up to 10 concurrent real calls, GhostShield-mediated, hard-capped at MAX_ACTIVE_WORKERS<=10 / INFERENCE_WORKER_MAX_USD<=$25 per session; verified REAL_LIVE 2026-09-27 (see M20_REALITY_MATRIX.md) |

## What remains simulated

Director observations, adversarial search, Arena ranges, default worker path, much of UI replay.

## Enterprise deployment would require

Multi-tenant isolation, auth/IAM, Shield bypass closure, live Arena, formal backup/restore drills, SOC integrations.

## Commands

```bash
scripts/m20-release-check.sh
scripts/m20-golden-path.sh   # mock against local API
ALLOW_M20_LIVE_CAMPAIGN=true M20_LIVE_CAMPAIGN_MAX_USD=15 scripts/m20-golden-path.sh
```

---

**GhostRange does not ask an AI what is wrong and trust the answer** — but M20 **does not yet SHIP** as a complete production proof of every bullet in the vision deck.
