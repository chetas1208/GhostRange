# M4 Coordination — GhostScheduler Intelligence

Lead agent owns integration, contract freeze, and conflict resolution. **26 specialist workstreams** (prompt §57); do not edit another agent's owned paths without updating this file.

## Contract freeze (after Wave 1)

`SchedulingContextV3`, `SchedulingPlanV3`, `TaskResourceProfileV2`, `WorkerResourceProfileV2`, `TaskLatencyModelV1`, `ComputeCostModelV1`, `RuntimeDistributionV1`, `ReasoningBudgetV1`, `EvidenceValueModelV1`, `SchedulerTraceV1` — versioned additive changes only.

## Agent table

| agent_id | mission | owned_paths | dependencies | status | blockers | deliverables | integration_status |
|----------|---------|-------------|--------------|--------|----------|--------------|-------------------|
| 01 | M4 audit | `docs/milestones/M4_AUDIT.md` | — | **done** | M3 incomplete | Audit + classifications | merged |
| 02 | Scheduling literature | `docs/research/M4_SCHEDULING_SYNTHESIS.md` | — | **done** | — | 10+ paper entries | merged |
| 03 | V3 contracts | `packages/contracts/scheduler/`, `ghostrange_contracts/scheduler_v3.py` | 01 | **done** | — | Context/plan V3 | merged |
| 04 | Task profiles | `packages/scheduler/ghostrange_scheduler/profiling/task_profile.py` | 03 | planned | — | TaskResourceProfileV2 helpers | — |
| 05 | Worker profiles | `packages/scheduler/ghostrange_scheduler/profiling/worker_profile.py` | 03 | planned | — | WorkerResourceProfileV2 helpers | — |
| 06 | Latency model | `packages/scheduler/ghostrange_scheduler/models/latency.py` | 03,04 | **started** | no live calibration | TaskLatencyModelV1 + EMA | partial |
| 07 | Cost model | `packages/scheduler/ghostrange_scheduler/models/cost_model.py` | 03 | **started** | placeholder rates | ComputeCostModelV1 | partial |
| 08 | CPU/GPU placement | `packages/scheduler/ghostrange_scheduler/v3/placement.py` | 04,06,07 | planned | — | Heterogeneous placement | — |
| 09 | Serverless routing | `packages/scheduler/ghostrange_scheduler/v3/inference_route.py` | 03,18 | planned | — | ROUTE_INFERENCE actions | — |
| 10 | Critical path | `packages/scheduler/ghostrange_scheduler/v3/critical_path.py` | 03 | **done** | — | slack + CP membership | merged |
| 11 | Branch priority | `packages/scheduler/ghostrange_scheduler/v3/branch_priority.py` | 03 | planned | no live branches | branch urgency | — |
| 12 | Queue model | `packages/scheduler/ghostrange_scheduler/v3/queue.py` | 03 | **started** | — | QueueStateV1 metrics | partial |
| 13 | Autoscale | `packages/scheduler/ghostrange_scheduler/v3/autoscale.py` | 12,07,config | planned | API wiring | scale out/in + hysteresis | — |
| 14 | Stragglers | `packages/scheduler/ghostrange_scheduler/v3/straggler.py` | 06 | planned | — | RuntimeDistributionV1 + class | — |
| 15 | Speculation | `packages/scheduler/ghostrange_scheduler/v3/speculation.py` | 14 | planned | — | SPECULATE + cancel accounting | — |
| 16 | Fragmentation | `packages/scheduler/ghostrange_scheduler/v3/fragmentation.py` | 04,05,08 | planned | — | placement failure metrics | — |
| 17 | Preemption | `packages/scheduler/ghostrange_scheduler/v3/preemption.py` | 03 | planned | — | sim-only preemption | — |
| 18 | Adaptive inference | `packages/scheduler/ghostrange_scheduler/v3/reasoning_budget.py` | 03,09 | planned | — | ReasoningBudgetV1 | — |
| 19 | Evidence value | `packages/scheduler/ghostrange_scheduler/v3/evidence_value.py` | 03 | planned | — | EvidenceValueModelV1 | — |
| 20 | Stopping | extend `stopping.py` + v3 | 19 | planned | — | STOP_MARGINAL_GAIN_LOW optional | — |
| 21 | Simulator | `packages/scheduler/ghostrange_scheduler/simulator/` | 03,22 | **started** | — | GhostSchedulerSimulator | partial |
| 22 | Benchmarks | `benchmarks/`, `artifacts/benchmarks/m4/` | 21 | planned | — | baselines + stats | — |
| 23 | Vultr calibration | `artifacts/calibration/vultr/` | vultr-control | planned | credentials | measured startup/runtime | — |
| 24 | Execution UI | `apps/web/src/ui/scenes/ExecutionScene.tsx`, selectors | API events | planned | React #185 | CP, queue, scale, speculation | — |
| 25 | Perf stress | `scripts/`, web tests | 24 | planned | — | high event rate fixture | — |
| 26 | Integrity gate | `docs/milestones/M4_FINAL.md`, `M4_BENCHMARK_REPORT.md` | all | planned | — | fairness + negative results | — |

## Waves

| Wave | Agents | Gate |
|------|--------|------|
| 0 | 01, 02 | Audit + synthesis |
| 1 | 03, 04, 05, 06, 07, 21 | Contract freeze + simulator skeleton |
| 2 | 08, 09, 10, 11, 12, 13, 16 | Core v3 plan |
| 3 | 14, 15, 17, 18, 19, 20 | Straggler, speculation, adaptive |
| 4 | 22, 23 | Benchmarks + calibration |
| 5 | 24, 25 | UI + stress |
| 6 | 26 | Release gate |

## Do-not-touch (unless lead + coordination update)

- M2 UI selector stability patterns (`useShallow`, `useMemo`) — Agents 24–25 only, minimal diff  
- `packages/events` event names without Agent 19/lead sync  
- Production deployment paths outside GhostRange worlds  

## Shared read-only

`docs/architecture/GHOSTSCHEDULER_V3.md`, `config/ghostscheduler-v3.yaml`, `Progress.md`
