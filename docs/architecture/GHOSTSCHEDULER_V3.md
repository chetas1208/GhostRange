# GhostScheduler V3

Policy version: `ghostscheduler/v3`

## Entrypoints

| API | Role |
|-----|------|
| `ghostrange_scheduler.schedule()` | **V1** — single-task `SchedulerDecisionV1` (M2, still used by M2 API orchestrator) |
| `ghostrange_scheduler.v3.plan()` | **V3** — multi-action `SchedulingPlanV3` from `SchedulingContextV3` |

V3 does **not** replace V1 in the API until orchestrator migration (post–M4 Wave 2).

## Input: `SchedulingContextV3`

Aggregates tasks, profiles, workers, DAG edges, budget, latency/cost models, queue metrics, fragmentation, and mandatory-task ids (safety).

Configuration: `config/ghostscheduler-v3.yaml`.

## Output: `SchedulingPlanV3`

Ordered `PlanActionV1` list. Each action carries:

- `action` (`PLACE_TASK`, `PROVISION_WORKER`, `ROUTE_INFERENCE`, …)
- `reason_codes` (explainability)
- `input_features`, `estimated_*`, `confidence`, `constraints_considered`

## Safety

Mandatory verification task ids in `mandatory_task_ids` — stopping and deferral policies must not skip them (enforced in plan + future runtime).

Failsafe policy: `FIXED_POOL_SAFE` (config).

## Modules (M4)

- `v3/critical_path.py` — slack + CP membership
- `v3/queue.py` — queue pressure
- `v3/placement.py` — fit + FIRST/BEST fit
- `v3/plan.py` — orchestrates actions
- `simulator/engine.py` — deterministic simulation

## Benchmarks

Target: `artifacts/benchmarks/m4/` via Agent 22 (not yet populated).
