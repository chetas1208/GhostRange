# M2 Completion Audit — 2026-09-26 (re-verified)

Method: read source + run commands. Do not trust prior agent summaries.

## Commands run (this audit)

| Command | Result |
|---------|--------|
| `npm run typecheck` | pass |
| `npm run test` (apps/web) | 7/7 pass |
| `npm run build` | pass |
| `pip install -e packages/* + apps/api[dev]` | ok |
| `pytest packages/contracts` | **66** passed |
| `pytest packages/events` | **115** passed |
| `pytest packages/evidence` | **32** passed |
| `pytest packages/vultr-control` | **91** passed |
| `pytest packages/range-iac` | **24** passed |
| `pytest packages/range-runtime` | **153** passed |
| `pytest packages/scheduler` | **115** passed |
| `pytest packages/policy-check` | **40** passed |
| `pytest apps/api` (mock M2 E2E) | **1** passed |

**Python total (installed venv):** 637 tests passing (636 package + 1 API E2E).

Git: **no commits yet** (`git status` — entire tree untracked).

---

## Subsystem status

| Subsystem | Status | Notes |
|-----------|--------|-------|
| **apps/web UI** | **COMPLETE** | Fixture + live hooks; React #185 fixed; 12 §38 PNGs; **protected — do not redesign** |
| **packages/ui-3d** | **COMPLETE** | R3F primitives |
| **packages/contracts** | **COMPLETE** | Schemas + tests |
| **packages/events** | **LIVE_READY** | Registry + `world.destroying` additive; Postgres/Redis store in `ghostrange_events.store` |
| **packages/vultr-control** | **LIVE_READY** | `RealVultrProvider` + `MockVultrProvider`; 91 unit tests; **not LIVE_VERIFIED** without `VULTR_API_KEY` |
| **packages/range-iac** | **LIVE_READY** | Compiler + cloud-init + apply; auth-lab range on disk |
| **packages/range-runtime** | **LIVE_READY** | State machine + SQLite persistence + vultr adapter; 153 tests |
| **packages/scheduler** | **COMPLETE** | Real `schedule()` → `SchedulerDecisionV1` + reason codes |
| **packages/policy-check** | **COMPLETE** | `PolicyCheckService.authorize()` |
| **packages/evidence** | **COMPLETE** | Artifact store + deterministic `evaluate_auth_lab_v1` |
| **apps/api** | **PARTIAL → MOCK E2E** | FastAPI + memory SSE + `M2OneWorldOrchestrator`; mock pipeline E2E passes |
| **Live Postgres SSE path** | **PARTIAL** | `EventGateway` exists; **not wired as default** in `apps/api` (memory backend for M2 mock) |
| **Real Vultr E2E** | **MOCK_ONLY** | `GHOSTRANGE_LIVE_PROVIDER=vultr` path stubbed; requires credentials + live smoke |
| **Vultr Serverless Inference** | **EMPTY** | Agent 10 not implemented |
| **Execution harness (typed)** | **PARTIAL** | `apps/api/harness.py` — HTTP validation; not full policy-gated graph |
| **Orphan reconcile** | **PARTIAL** | `ghostrange-reconcile` CLI stub |
| **packages/adversary-adapter** | **EMPTY** | Caldera adapter pending |
| **packages/execution-graph** | **EMPTY** | Contracts only |

---

## M2 exit condition (honest)

| Criterion | State |
|-----------|--------|
| RangeSpec validates | **yes** (`ranges/ghostrange-auth-lab-v1/rangespec.yaml`) |
| Policy enforcement | **code yes**, not in full API loop yet |
| GhostScheduler real decisions | **yes** (orchestrator emits `scheduler.decision`) |
| Vultr provider | **code yes**, live **NOT_RUN** without creds |
| Real range provisions | **no** (mock provider in default API run) |
| Controlled execution | **simulated HTTP** in mock run |
| Evidence persisted | **events yes**; object store not wired in API yet |
| Deterministic verification | **yes** (`evaluate_auth_lab_v1`) |
| Live SSE | **yes** (memory backend) |
| UI consumes live events | **ready** (`VITE_DATA_SOURCE=live` + `VITE_RANGE_ID`) |
| Teardown + provider confirm | **mock teardown** via range-runtime; **no live confirm** |
| Mock E2E | **pass** (`apps/api/tests/test_mock_m2_e2e.py`) |
| Live Vultr E2E | **NOT_RUN_NO_CREDENTIALS** |

---

## Next integration order (lead agent)

1. Wire `apps/api` to Postgres `EventGateway` when `POSTGRES_DSN` set (keep memory for CI).
2. Connect `range-iac` apply + `RealVultrProvider` behind `GHOSTRANGE_LIVE_PROVIDER=vultr`.
3. Health-check gateway container stack before `world.ready`.
4. Policy-check on every `ExecutionRequestedV1`.
5. Real E2E gate + `artifacts/benchmarks/m2-live.json`.
6. First git commit baseline (no secrets).
