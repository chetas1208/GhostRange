# Realtime timing model (UI contract)

## Goal

Every visible operation should eventually expose the fields in §6 of the tactical spec. **Today**, the frontend only has reliable **event timestamps** and **run-level benchmark** JSON from the API.

## Implemented today

### Event timestamps

- Each `GhostEvent` carries `occurred_at` (ISO-8601).
- `eventLog[]` stores `{ occurred_at, label }` for HUD/ticker.
- Frontend elapsed timers **derive** `Date.now() - started_at` client-side; no 100 ms polling of backend.

### Run benchmark (`RunBenchmark`)

Source: `apps/api/ghostrange_api/orchestrator.py`, exposed at:

`GET /v1/ranges/{range_id}/benchmark` (see `apps/api/ghostrange_api/main.py`).

Fields (milliseconds unless noted):

| Field | Meaning |
|-------|---------|
| `provisioning_ms` | Provision + boot window (mock pipeline) |
| `boot_ms` | Currently mirrored to provisioning in M2 |
| `execution_ms` | Experiment execution window |
| `verification_ms` | Verification window |
| `teardown_ms` | Teardown window |
| `total_ms` | Wall clock for run |
| `estimated_cost_usd` | Accumulated estimate from scheduler/events |

**Estimate source today:** `STATIC_CONFIG` / orchestrator wall clock — **not** historical P50.

### Scheduler (package contracts)

`packages/contracts/ghostrange_contracts/scheduler_m15.py` defines CPM reports with `estimated_duration_seconds` — used in scheduler packages, **not wired to web store**.

## Target: `OperationTimingV1` (frontend mirror)

```typescript
export type EstimateSource =
  | 'HISTORICAL_P50'
  | 'HISTORICAL_P95'
  | 'PROVIDER_ESTIMATE'
  | 'STATIC_CONFIG'
  | 'SCHEDULER_ESTIMATE'
  | 'MODEL_ESTIMATE'
  | 'INSUFFICIENT_DATA';

export interface OperationTimingV1 {
  operation_id: string;
  operation_type: string;
  status: string;
  queued_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  queue_wait_ms?: number | null;
  elapsed_ms?: number | null;
  estimated_duration_ms?: number | null;
  estimated_remaining_ms?: number | null;
  estimate_source?: EstimateSource;
  estimate_confidence?: 'LOW_SAMPLE_COUNT' | 'MEDIUM' | 'HIGH' | null;
  retry_count?: number;
  failure_reason?: string | null;
}
```

**UI rule:** if `estimated_duration_ms == null` → show **ESTIMATE UNAVAILABLE**, not a guess.

## Duration decomposition (target)

Map operation types to buckets:

| Bucket | Event hints (existing) |
|--------|-------------------------|
| QUEUE | `task.queued` → `task.started` |
| PROVISION | `compute.requested` → `compute.ready` |
| EXECUTION | `task.started` / `execution.started` → completed |
| VERIFICATION | `verification.started` → `verification.passed` |
| TEARDOWN | `world.destroying` → `world.destroyed` |

Tasks in `GhostState` **lack** per-task timestamps until reducer stores first/last event times per task (planned adapter).

## Historical estimation (not implemented)

Requirements:

- Persist completed operations with `operation_type`, `duration_ms`, `provider`, `resource_class`.
- Compute P50/P90/P95 only when `sample_count >= MIN_SAMPLES` (recommend 8+).
- Emit `estimate_confidence: LOW_SAMPLE_COUNT` otherwise.

Reuse: `artifacts/benchmarks/*.json` writes from orchestrator as seed aggregator.

## Hook: `useOperationTimer` (Phase 1)

- Campaign elapsed: first `eventLog` or live buffer `occurred_at` → now (live) or frozen (replay scrub).
- Remaining: **null** until historical API exists.

## Related

- `TACTICAL_UI_AUDIT.md`
- `apps/web/src/hooks/useRangeBenchmark.ts` (Phase 1)
