# M20 Live Deploy Status — independent verification (2026-09-27, ~06:20 UTC)

**Method:** not a claims review of the four parallel agents' own reports. Every line below was
checked directly this pass: real `curl` against the public IP and against a freshly-run local
process, a real `pytest` run of the bypass-audit + adapter tests, a real run of
`scripts/m20-release-check.sh`, and direct file reads of the current state of the four target
docs/modules. Taxonomy follows `docs/release/M20_REALITY_MATRIX.md`: `REAL_LIVE` (real prod
traffic/infra, no shortcuts), `CONTROLLED_LIVE` (real external service, gated/small-scale),
`SIMULATED` (in-process, no external effect), `NOT_RUN`.

## 1. Public URL — is there a working one right now?

**Yes, one URL answers right now, but it is serving stale (pre-M20) code.**

- `http://45.76.248.45` — `GHOSTRANGE_CONTROL_HOST` / `GHOSTRANGE_PUBLIC_URL` from `.env` / `.env.production`.
- Verified this pass:
  - `GET http://45.76.248.45/health/live` → `HTTP 200`, body `{"ok":true,"deploy_sha":"prod-v4-worker","live_provider":"vultr"}`. **REAL_LIVE** (real Caddy → real container on the Vultr control VM, checked twice, ~5 min apart, both 200).
  - `GET http://45.76.248.45/` → `HTTP 200`, serves the real GhostRange frontend `index.html` (title "GhostRange — The Cyber Multiverse"). **REAL_LIVE**.
  - `POST http://45.76.248.45/v1/campaigns/golden` (the M20 canonical golden-campaign route) → **`HTTP 404`**. This route exists in the current repo (`campaign_routes.py`, registered in `main.py`, covered by `apps/api/tests/test_m20_campaign.py`) but the *deployed* container does not have it.
  - `POST http://45.76.248.45/v1/golden-path/runs` (legacy M10 route) → `HTTP 200`, and its response is self-describing old code: `"teardown": "LIVE_NOT_IMPLEMENTED_IN_M10_SLICE"`.
  - `GET http://45.76.248.45/v1/scheduler/inference-workers/guardrails` (new inference-worker-pool route, added this session) → `HTTP 404`.

**Conclusion: the running control-VM container predates the M20 campaign route, the M20 GhostShield-bypass fix, and the new inference-worker pool.** The public IP is real and up, but it is not currently serving the code state this report verifies below on disk. Nothing has been redeployed to the VM during this verification window. Do not tell the user "the M20 golden path is live at that URL" — it isn't; only the old health/frontend/legacy-M10 surface is.

- Local: no local instance of the current `ghostrange_api` app was found running (the only thing listening on `127.0.0.1:8000` is an unrelated stale Python process from Sept 10, not this repo's API). `docker ps` locally shows only `ghostrange-postgres-dev` / `ghostrange-valkey-dev` (dev-compose infra, 28h uptime) — no `docker-compose.prod.yml` stack running on this machine, which is expected since prod runs on the separate control VM.
- SSH to the control VM (`scripts/vultr-ssh.sh`, same key/creds path a deploy agent would use) **failed during this session** (`paramiko.ssh_exception.AuthenticationException`) — could not independently confirm `docker compose ps` on the VM itself. This is a real limitation of this verification pass, not a claim that the VM is down (the HTTP checks above prove containers are up); I simply could not get a second, container-level confirmation of *which* image/tag is running beyond what `/health/live`'s `deploy_sha: prod-v4-worker` and the 404s above already imply.

## 2. GhostShield policy-bypass — actually closed?

**Yes, for the destructive paths — verified by running the tests myself, not by reading the doc.**

Ran directly this pass:
```
python3 -m pytest -q apps/api/tests/test_ghostshield_bypass_audit.py \
  apps/api/tests/test_ghostshield_enforce.py \
  apps/api/tests/test_ghostshield_vultr_adapter.py
→ 8 passed in 0.54s
```
and the full `scripts/m20-release-check.sh` (below) which includes this suite plus the wider
`packages/ghostshield/tests` policy-engine suite — all passing, `fail=0`.

Cross-checked against the current `docs/security/GHOSTSHIELD_BYPASS_ANALYSIS.md` (updated this
session): `compute_provider.py` and `orchestrator.py` (the two create/destroy call sites) now
both route through `GhostExecutionGateway` via `ShieldedComputeProvider` / new
`ShieldedVultrAdapter`; `GHOSTSHIELD_MODE=DISABLED` is the only unshielded escape hatch and it's
an explicit env var, not a default. One path remains intentionally un-gated:
`scheduler_routes.py`'s `compute_dry_check`, which only calls read-only `list_computes()` — no
create/destroy capability, so it's a documented, reasoned exception rather than a leftover hole.

**Classification: CONTROLLED_LIVE at the policy-engine/unit-test level.** This is real code
mediating real call sites, verified by real tests I ran — but, as `M20_REALITY_MATRIX.md` itself
now (correctly) notes, it has **not yet been exercised against a live Vultr worker end-to-end**
(no live create→gateway-deny/allow→destroy cycle was run this session against real Vultr
Compute). The bypass is closed in the code; it is not yet proven closed under a real live
worker load.

## 3. 10-concurrent Serverless Inference workers — actually running?

**Code exists and is well-built; it is not deployed, and no real concurrent Vultr Inference
calls were observed to have happened.**

- New module `apps/api/ghostrange_api/inference_worker_pool.py` + `inference_worker_routes.py`
  (both created this session, read in full this pass): real `asyncio.Semaphore`-bounded fan-out
  of real HTTP calls to `https://api.vultrinference.com/v1/chat/completions`, hard-clamped to
  `min(MAX_ACTIVE_WORKERS, 10)`, mediated through `GhostExecutionGateway` with a real budget
  guard (hard ceiling $25, per-call estimate $0.05, both enforced in-process and via the gateway's
  policy engine). This is genuine, not a mock stub — `_effect()` calls the real `InferenceService`,
  and errors from the real HTTP layer are surfaced, not swallowed.
- **Effective concurrency as configured right now is 1, not 10.** `.env.production` still has
  `MAX_ACTIVE_WORKERS=1` — `inference_worker_concurrency_cap` = `min(1, 10)` = 1. The 10-worker
  ceiling is a cap, not the operating value; nothing currently sets it to 10 in the deployed
  config.
- **Not reachable on the public URL** — `GET /v1/scheduler/inference-workers/guardrails` → 404
  on `http://45.76.248.45`, confirming this code has not been built into the running control-VM
  image.
- No log file, benchmark JSON, or test artifact was found anywhere in the repo showing a
  completed real dispatch (`max_observed_concurrency > 1` from an actual run). I did not trigger
  a real paid batch call myself in this pass (that would create the first evidence rather than
  verify existing evidence, and risks real spend against `VULTR_INFERENCE_API_KEY` without the
  requesting agent's sign-off).

**Classification: NOT_RUN (real concurrent workers).** Code: real and reasonably designed.
Configuration: capped at 1. Deployment: not present on the live VM. No evidence of an actual
concurrent real call.

## 4. Real live golden-path campaign — did one complete?

**No.** No artifact, benchmark JSON, or log anywhere in the repo shows a completed
`ALLOW_M20_LIVE_CAMPAIGN=true` run. `docs/milestones/M20_FINAL.md` (unchanged this session) still
states live campaign is `NOT_RUN`, requiring `ALLOW_M20_LIVE_CAMPAIGN=true` + Vultr ACL + VPC +
Postgres worker store. `docs/milestones/M20_COORDINATION.md` still shows agent 11 (worker fleet
live) and agent 25 (Vultr compute finalization) as `blocked` (Vultr ACL). The mock golden path
(`POST /v1/campaigns/golden` against a local ASGI transport, no network) does pass —
`test_m20_campaign.py`, re-verified in this pass via `m20-release-check.sh` — but that is
**SIMULATED**, per the matrix's own labeling, not a live run.

## 5. What I ran for real, this pass

| Check | Result |
|---|---|
| `scripts/m20-release-check.sh` (full, local) | `fail=0` — 423 passed/1 skipped unit+integration, web typecheck clean, 7/7 vitest, 21 GhostArena/Evolve/Shield/Runtime package tests, 2/2 M20 mock campaign API, Arena sim → `QUALIFIED` |
| `pytest apps/api/tests/test_ghostshield_bypass_audit.py test_ghostshield_enforce.py test_ghostshield_vultr_adapter.py` | 8 passed |
| `curl http://45.76.248.45/health/live` (x2, ~5 min apart) | 200, `{"ok":true,...}` both times |
| `curl http://45.76.248.45/` | 200, real frontend HTML |
| `curl -X POST http://45.76.248.45/v1/campaigns/golden` | **404** — M20 route not deployed |
| `curl -X POST http://45.76.248.45/v1/golden-path/runs` | 200, but body proves pre-M20 (M10) code |
| `curl http://45.76.248.45/v1/scheduler/inference-workers/guardrails` | **404** — inference-worker route not deployed |
| SSH to control VM (`scripts/vultr-ssh.sh`) | **Failed** (auth error) — could not confirm `docker compose ps` on the VM directly |
| `docker ps` (local) | only dev postgres/valkey; no prod stack on this host (expected) |

## Bottom line by the matrix taxonomy

| Item | Status |
|---|---|
| Public URL answering | **REAL_LIVE** (health + frontend only) |
| Public URL serving current M20 code (campaign route, shield fix, inference pool) | **NOT_RUN** (not deployed) |
| GhostShield bypass closed (code + unit/integration tests) | **CONTROLLED_LIVE** |
| GhostShield bypass proven under a live worker end-to-end | **NOT_RUN** |
| 10-concurrent Serverless Inference workers, real calls | **NOT_RUN** (code exists; configured cap=1; not deployed; no evidence of a real run) |
| Real live golden-path campaign completion | **NOT_RUN** |
| Mock golden-path campaign | **SIMULATED** (passes) |
