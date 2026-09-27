# M15 Coordination — 48 specialist agents

**Lead:** architecture, contract freeze, budget authority, integration, Agent 48 gate.  
**Live compute:** OFF for elastic fleet until real-worker GO. Simulator-first default.

Status: `planned` | `active` | `review` | `done` | `blocked`

## Prerequisite banner

Real-worker milestone: **NO-GO** → agents 43, 47 live paths **blocked** except dry-run estimates.

## Waves

| Wave | Agents | Gate |
|------|--------|------|
| 0 | 01, 02 | `M15_AUDIT.md` + `M15_ADAPTIVE_SCHEDULING_SYNTHESIS.md` |
| 1 | 03–09 | Contract freeze Wave 1 |
| 2 | 10–17 | Cost/placement models |
| 3 | 18–21 | Parallelism + speculation |
| 4 | 22–27 | Elastic fleet |
| 5 | 28–35 | Quality/compute + provenance |
| 6 | 36–42 | Simulator + baselines |
| 7 | 43–45 | Live + UI (**blocked**) |
| 8 | 46–47 | Chaos + red team |
| 9 | 48 | GO / NO-GO |

## Roster (48)

| ID | Role | Owned paths (write) | Status | Live? |
|----|------|---------------------|--------|-------|
| 01 | M15 audit lead | `docs/milestones/M15_AUDIT.md` | done | no |
| 02 | Scheduling research | `docs/research/M15_ADAPTIVE_SCHEDULING_SYNTHESIS.md` | done | no |
| 03 | DAG contract | `scheduler_m15.py` | active | no |
| 04 | DAG validation | `scheduler_m15.py`, tests | active | no |
| 05 | Critical path | `ghostrange_scheduler/m15/critical_path.py` | active | no |
| 06 | Priority | `scheduler_m15.py` | planned | no |
| 07 | Task resource profiler | profiles in m15 | planned | no |
| 08 | Worker resource profiler | profiles + catalog | planned | no |
| 09 | Vultr worker class | `config/worker_classes.yaml` (TBD) | planned | no |
| 10 | CPU/GPU placement | crossover model | planned | no |
| 11 | Startup latency | calibration from live worker | **blocked** | yes |
| 12 | Runtime estimation | `RuntimeEstimatorV1` TBD | planned | no |
| 13 | Cost model | extend v3 cost model | planned | no |
| 14 | Task/VM sensitivity | benchmarks | planned | no |
| 15 | Warm worker | retention decision | planned | no |
| 16 | Bin packing | packing policy | planned | no |
| 17 | Interference | co-location metrics | planned | no |
| 18 | Parallelism | `ParallelismPlanV1` TBD | planned | no |
| 19 | Speculation architect | `SpeculationDecisionV1` TBD | planned | no |
| 20 | Straggler | `StragglerModelV1` TBD | planned | no |
| 21 | Speculation cancel | lease/artifact rules | planned | no |
| 22 | Fleet state | `FleetStateV1` TBD | planned | no |
| 23 | Scale-out | `ScaleDecisionV1` TBD | planned | no |
| 24 | Scale-in | drain/TTL | planned | no |
| 25 | Cooldown/thrash | policy | planned | no |
| 26 | Deadlines | feasibility | planned | no |
| 27 | Budget | `SchedulerBudgetV2` | active | no |
| 28 | Marginal compute value | `MarginalComputeValueV1` TBD | planned | no |
| 29 | Stopping policy | `ComputeStoppingDecisionV1` TBD | planned | no |
| 30 | Director bridge | director handshake | planned | no |
| 31 | GhostCausal scheduling | factorial parallel | planned | no |
| 32 | GhostMesh savings | metrics | planned | no |
| 33 | GhostWatch priority | urgency queue | planned | no |
| 34 | Decision provenance | `SchedulerDecisionV2` | active | no |
| 35 | Online learning | runtime updates | planned | no |
| 36 | Simulator v2 | `GhostSchedulerSimulatorV2` TBD | planned | no |
| 37 | Baselines | FIFO/HEFT/… | planned | no |
| 38 | Oracle | small DAG ILP | planned | no |
| 39 | Speculation bench | `artifacts/benchmarks/m15/speculation/` | planned | no |
| 40 | Elasticity bench | `artifacts/benchmarks/m15/elasticity/` | planned | no |
| 41 | Heterogeneous bench | `artifacts/benchmarks/m15/cpu-gpu/` | planned | no |
| 42 | Quality/cost bench | diminishing returns | planned | no |
| 43 | Live Vultr E2E | scripts + campaigns | **blocked** | yes |
| 44 | Execution 3D UI | `apps/web` Execution | planned | no |
| 45 | Evidence UI | cost/decision panels | planned | no |
| 46 | Chaos | failure injection | planned | sim |
| 47 | Cost red team | budget bypass tests | planned | sim |
| 48 | Final reviewer | `M15_FINAL.md` | **NO-GO** | — |

Integration owner: lead agent. Conflicts: Director vs Scheduler boundaries per §4–5 prompt.
