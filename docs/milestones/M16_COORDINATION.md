# M16 Coordination — 50 specialist agents

**Lead:** runtime architecture, contract freeze, recovery policy, side-effect safety, Agent 50 gate.  
**Not in scope:** new Director/Causal/Scheduler intelligence — durability only.

Live chaos: **`ALLOW_M16_LIVE_CHAOS=false`** default; max 2 workers; no GPU.

## Waves

| Wave | Agents | Gate |
|------|--------|------|
| 0 | 01–02 | Audit + reliability synthesis |
| 1 | 03–08 | Wave 1 contract freeze |
| 2 | 09–15 | Checkpoint + recovery + reconciliation |
| 3 | 16–23 | Task/effect safety + budgets |
| 4 | 24–31 | Subsystem recovery + events |
| 5 | 32–36 | Ops + invariants + reaper |
| 6 | 37–43 | GhostChaos |
| 7 | 44–47 | Benchmarks + UI |
| 8 | 48–49 | Red team |
| 9 | 50 | GO / NO-GO |

## Roster (50)

| ID | Mission | Owned paths | Status | Live |
|----|---------|-------------|--------|------|
| 01 | M16 audit | `M16_AUDIT.md` | done | no |
| 02 | Reliability research | `M16_RELIABILITY_SYNTHESIS.md` | done | no |
| 03 | Canonical state | `ghostruntime_m16.py` | active | no |
| 04 | Runtime FSM | lifecycle transitions (TBD) | planned | no |
| 05 | Command/event | `RuntimeCommandV1`/`RuntimeEventV1` | active | no |
| 06 | Side-effect journal | `runtime_side_effects` + store | planned | no |
| 07 | Idempotency | keys + unique constraints | active | no |
| 08 | Fencing/lease | `runtime_leases` | planned | no |
| 09 | Checkpoint architect | `CampaignCheckpointV1` | active | no |
| 10 | Checkpoint integrity | SHA-256 + corrupt CP test | planned | no |
| 11 | Event replay | `DeterministicRuntimeReplayV1` | planned | no |
| 12 | Recovery manager | `ghostrange_ghostruntime/recovery.py` | active | no |
| 13 | Provider reconciliation | Vultr vs PG | planned | yes |
| 14 | Worker reconciliation | worker + lease | planned | yes |
| 15 | Artifact reconciliation | registry vs S3 | planned | no |
| 16 | Task attempts | `task_attempts` | active | no |
| 17 | Speculation recovery | canonical vs loser | planned | no |
| 18 | Compensation/saga | `CompensationActionV1` | planned | no |
| 19 | Retry policy | `RetryBudgetV1` | planned | no |
| 20 | Circuit breakers | adapter layer | planned | no |
| 21 | Failure domains | `FailureDomainV1` | active | no |
| 22 | Safe mode | `RuntimeSafeModeV1` | planned | no |
| 23 | Budget recovery | persistent `budget_spent_usd` | planned | no |
| 24 | Director recovery | director revision in CP | planned | no |
| 25 | Scheduler recovery | DAG/fleet in CP | planned | no |
| 26 | Causal recovery | causal revision | planned | no |
| 27 | Mesh degradation | `NO_MESH` profile | planned | no |
| 28 | GhostWatch recovery | no repeat prod actions | planned | no |
| 29 | GhostGate recovery | approval binding | planned | no |
| 30 | Model durability | frozen model outputs | planned | no |
| 31 | Event ordering | dedupe + aggregate seq | planned | no |
| 32 | SSE/frontend recovery | bootstrap from PG | planned | no |
| 33 | Pause/resume | runtime API | planned | no |
| 34 | Abort/cleanup | drain + terminate | planned | yes |
| 35 | Resource reaper | ownership-safe | planned | yes |
| 36 | Runtime invariants | checker job | planned | no |
| 37 | GhostChaos harness | `packages/ghostruntime/chaos/` TBD | planned | sim |
| 38 | Process/VM crash | container restart tests | planned | sim |
| 39 | DB chaos | PG outage | planned | sim |
| 40 | Object storage chaos | S3 outage | planned | sim |
| 41 | Vultr API chaos | UNKNOWN effect | planned | sim |
| 42 | Worker/network chaos | partition/stale | planned | sim |
| 43 | Model chaos | inference fail | planned | sim |
| 44 | Reliability benchmark | horizon sweeps | planned | sim |
| 45 | Checkpoint perf | overhead metrics | planned | no |
| 46 | Execution 3D UI | `<CheckpointAnchor />` etc. | planned | no |
| 47 | Evidence/failure UI | recovery provenance | planned | no |
| 48 | Duplicate-effect red team | security tests | planned | sim |
| 49 | Cost/orphan red team | budget + workers | planned | sim |
| 50 | Final reviewer | `M16_FINAL.md` | **NO-GO** | — |

Failure cases tracked per agent in integration_status field during waves 2–8.
