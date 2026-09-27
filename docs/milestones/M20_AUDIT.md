# M20 Global Audit — repository truth (Wave 0)

**Date:** 2026-09-27  
**Branch:** `master` (no commits yet — entire tree untracked)  
**Method:** doc review + code inspection + `scripts/run-all-tests.sh` + targeted pytest

## Capability matrix (summary)

| Subsystem | Class | Evidence |
|-----------|-------|----------|
| Range compiler (compose → graph) | REAL_LOCAL_ONLY | `GoldenPathOrchestrator._compile_source`, range-compiler tests |
| Living twin / drift | PARTIAL | M6 unit tests; not wired into M20 HTTP campaign |
| GhostDirector (auth incident) | REAL_LOCAL_ONLY | 3 hypotheses in `auth_incident.py`; simulator in golden path |
| GhostScheduler V3 | REAL_LOCAL_ONLY | plan-preview API + golden path plan |
| Vultr workers | REAL_CONTROLLED_LIVE / BROKEN | Code path exists; **Vultr API ACL** blocked control VM IP in ops notes |
| Object Storage | REAL_CONTROLLED_LIVE | production roundtrip route when configured |
| Managed PostgreSQL | REAL_CONTROLLED_LIVE | event store when `POSTGRES_DSN` + Redis |
| Serverless Inference | REAL_CONTROLLED_LIVE | ops smoke when key set |
| GhostCausal | SIMULATED | API simulate routes; not in golden HTTP chain |
| GhostMesh | SIMULATED | harness/API; not golden path |
| GhostGate | PARTIAL | promotion after golden; human gate |
| GhostWatch | SIMULATED | simulator routes |
| GhostRuntime | REAL_LOCAL_ONLY | package tests; **not** restart recovery in M20 campaign |
| GhostShield | PARTIAL | ENFORCE wrapper; M17 bypass routes (`orchestrator.py` / `vultr_adapter.py`) closed 2026-09-27 via `ShieldedVultrAdapter` — see GHOSTSHIELD_BYPASS_ANALYSIS.md. Still PARTIAL: enforcement verified against mock provider + policy engine, not yet exercised against a live Vultr worker end-to-end |
| GhostEvolve | PARTIAL | store + promotion; Arena gate wired |
| GhostArena | SIMULATED | hidden suite sim; qualifies `qualified` policy |
| GhostLedger | REAL_LOCAL_ONLY | seal/verify in golden path |
| Frontend 3D | FIXTURE_ONLY / PARTIAL | replay fixture; production state wiring incomplete |
| M20 unified campaign | REAL_LOCAL_ONLY | `POST /v1/campaigns/golden` |

## M1–M19 milestone docs

All M2–M19 FINAL docs present except M3 standalone FINAL (multiverse partial in M10). **Agent NO-GO** pattern: M10, M11–M19 finals cite blockers.

## Release blockers (top)

1. **No end-to-end live golden campaign** verified (`ALLOW_M20_LIVE_CAMPAIGN` + ACL + worker E2E).
2. **GhostShield bypass** paths — `compute_provider.py` was already gated; `orchestrator.py`'s live/mock `VultrAdaptedComputeProvider` path was not and has been closed 2026-09-27 (`ShieldedVultrAdapter`, tests in `apps/api/tests/test_ghostshield_vultr_adapter.py`). Remaining: enforcement is unit/policy-level only, not yet proven against a real Vultr worker in a live campaign.
3. **Runtime restart recovery** not demonstrated in one campaign.
4. **Causal / counterfactual / GhostWatch** not integrated into M20 HTTP golden chain.
5. **Frontend** still fixture-driven for full demo narrative.
6. **Git baseline** — no commits (release hygiene).

## Fiction removal (M20 rule)

- Mock golden path **labeled** `live_mode: mock` in benchmark JSON.
- M10 `teardown:LIVE_NOT_IMPLEMENTED` replaced at M20 route level by optional live worker hook (still blocked without flags/credentials).
- README status **updated** to match audit (was stale “M1 in progress”).

## Tests

- Python package + API tests: **pass** via `run-all-tests.sh`.
- Web typecheck: **fail** on unused locals (MeshSignal, arena props) — fix in progress for release check.

## Verdict

**NOT SHIP** — integration architecture documented; **RESEARCH_PROTOTYPE** maturity only.
