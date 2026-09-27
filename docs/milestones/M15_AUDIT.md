# M15 Audit — Wave 0 (2026-09-27)

Lead re-verified repository and production state before adaptive scheduling work.

## Prerequisite: real Vultr worker milestone

| Gate | Status |
|------|--------|
| One Vultr worker created (live) | **INCOMPLETE** — Vultr API IP ACL blocked `45.76.248.45` at last check |
| Worker register / lease / task on worker (live) | **INCOMPLETE** |
| Artifact + PG + teardown + `owned_workers=[]` (live) | **INCOMPLETE** |
| Agent 24 GO | **NO-GO** (`REAL_WORKER_FINAL.md`) |
| Mock worker runtime E2E on production | **REAL_VERIFIED** — `worker-benchmark` + in-process agent |

**M15 rule:** simulator + contracts + benchmarks **allowed**. **Elastic live-fleet experiments blocked** until prerequisite GO.

## Git / tests

| Check | Result |
|-------|--------|
| `git log` | No commits on `master` (uncommitted tree) |
| `pytest packages/scheduler packages/contracts apps/api/tests` | **213 passed**, 1 skipped |

## Component classification

| Area | Class | Notes |
|------|-------|-------|
| `WorkerScheduler` / `RealWorkerOrchestrator` | REAL_PARTIAL | Mock path verified; live path wired, not billable-proven |
| `worker_store` / leases / heartbeats | REAL_PARTIAL | Postgres + API; reconciliation/reaper missing |
| `VultrComputeProvider` | REAL_PARTIAL | Auth blocked by IP ACL until console fix |
| `MockComputeProvider` | REAL_VERIFIED | Mock lifecycle + orchestrator isolation when `live=False` |
| `ghostrange_worker` runtime | REAL_VERIFIED | CPU benchmark on worker via control plane |
| `scheduler_v3` + `plan()` | REAL_PARTIAL | Multi-action plans; not full DAG executor on live workers |
| `GhostSchedulerSimulator` (v1) | SIMULATED | Tick-based plan replay, not discrete-event DAG v2 |
| `ExperimentExecutionDAGV1` (Director) | READY_FOR_M15 | Handoff contract exists; map to `ExecutionDAGV2` |
| GhostCausal / GhostDirector / GhostLedger | INHERITED_BLOCKER | Integrate via handshake contracts; not full M15 wiring |
| Execution UI scheduler geometry | MOCK_ONLY | Fixture-driven; real worker events partial |
| GPU live workers | STUB | No `ALLOW_LIVE_GPU_TEST` path |
| M15 contracts (`scheduler_m15.py`) | **NEW Wave 1** | `ExecutionDAGV2`, CPM helper started |

## Blocking M15 live acceptance

1. Real worker **GO** (VPC + API ACL + one `--live` run).
2. `GHOSTRANGE_WORKER_VPC_ID` on production.
3. Startup reconciliation + `GhostWorkerReaper` (§129–131 prompt).
4. DAG execution engine bound to worker leases (not single-task orchestrator only).

## Ready for M15 (simulator-first)

- V3 profiles, cost/latency models, policy IDs, trace format.
- Critical-path prototype on `ExecutionDAGV2`.
- Baseline policy enum (`FIFO`, `HEFT_LIKE`, etc.) — implement in Wave 6.
- Research synthesis doc (Wave 0).
