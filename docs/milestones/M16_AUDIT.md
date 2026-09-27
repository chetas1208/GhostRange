# M16 Audit — Wave 0 (2026-09-27)

## Inherited gates

| Upstream | Status | Impact on M16 |
|----------|--------|----------------|
| Real worker live GO | **NO-GO** | Live chaos (Tests B/C) blocked; sim + contract work OK |
| M15 adaptive scheduler | **PARTIAL** | `ExecutionDAGV2` + CPM only; no FleetStateV1 engine |
| M15 Agent 48 | **NO-GO** | M16 does not depend on M15 GO for *durability* design |

M16 is **not** a new intelligence subsystem — it hardens execution substrate.

## Tests (2026-09-27)

| Suite | Result |
|-------|--------|
| `pytest packages/contracts packages/scheduler apps/api/tests` | 216+ passed (see CI/local) |
| `packages/events` store persistence (Redis tail) | **9 failures** without full Redis/pg harness — **INHERITED_BLOCKER** for SSE tail tests, not M16 core |

## Classification

| Component | Class | Notes |
|-----------|-------|-------|
| `event_log` + `range_seq_counters` | REAL_PARTIAL | Per-range seq, idempotent append; campaign-scoped runtime events **new** |
| `artifact_registry` + S3 | REAL_PARTIAL | Metadata PG; bytes in Object Storage |
| `worker_*` tables | REAL_PARTIAL | Leases exist; no recovery manager wired |
| `WorkerOrchestrator` finally teardown | REAL_PARTIAL | No intent journal before Vultr create |
| `reconcile.py` CLI | **STUB** | Dry-run placeholder only |
| GhostWorkerReaper | **MISSING** | Prompt §129 |
| Startup reconciliation | **MISSING** | Classic M16 hard case untested live |
| React/Zustand store | **NON_DURABLE** | Must bootstrap from PG on reconnect |
| SSE delivery | **NON_DURABLE** | Correct per §65 |
| GhostGate idempotency | REAL_PARTIAL | Promotion store only |
| GhostLedger checkpoints | REAL_PARTIAL | Event chain digest, not full campaign CP |
| `scheduler_m15` / v3 plans | READY_FOR_M16 | Scheduler recovery reads DAG/fleet from CP |
| M16 `ghostruntime_m16` contracts | **NEW Wave 1** | Canonical state + side effects |
| M16 PG schema (`campaign_runtime`, …) | **NEW** | Applied on schema bootstrap |
| `CampaignRecoveryManager` | **SIMULATED** | Deterministic policy stub + unit tests |

## Blocking M16 live acceptance

1. Wire **side-effect journal** into `VultrComputeProvider.create_worker` / terminate.
2. Implement **Postgres store** for `campaign_runtime` + optimistic revision.
3. **Runtime lease** (advisory lock or lease row) on campaign mutate.
4. **GhostChaos** harness + fault injection hooks (sim first).
5. Real worker GO for controlled live chaos (`ALLOW_M16_LIVE_CHAOS=false` default).

## Ready for M16 (immediate)

- Contract freeze Wave 1 (done in repo).
- Reliability synthesis + horizon benchmarks (simulator).
- Recovery unit tests for adopt-worker decision.
- Extend existing worker tables via `task_attempts` / `canonical_task_results`.
