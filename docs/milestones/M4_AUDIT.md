# M4 Audit — Wave 0 (2026-09-26)

Lead agent re-verified M3 scheduler/runtime claims before GhostScheduler Intelligence work. **Do not trust M3 summaries:** `M3_FINAL.md` does not exist; multiverse fork orchestration was not completed.

## Verified commands (this audit)

| Command | Result |
|---------|--------|
| `npm run typecheck` | pass |
| `npm run test` (web) | 7/7 pass |
| `pytest packages/contracts -q` | pass (70 tests, incl. M3 contract tests) |
| `pytest packages/scheduler -q` | pass (115 tests) |
| `scripts/run-mock-m2-e2e.sh` | pass (single-world M2 mock API) |
| `npm run build` | not re-run this audit (prior sessions: pass) |
| `git log` | **no commits yet** on `master` |

## M3 exit gate (prompt §89) — honest status

| Area | Status |
|------|--------|
| Real 3-child world fork + parallel verification | **NOT MET** — `apps/api` remains M2 one-world orchestrator |
| GhostScheduler V2 branch orchestration | **NOT MET** — contracts only (`SchedulingContextV2`, `SchedulerDecisionV2`) |
| M3 live benchmarks / screenshots | **NOT MET** — no `artifacts/benchmarks/m3/` |
| UI on real fork lifecycle | **PARTIAL** — fixture + reducer support; live fork stream absent |

M4 **does not require** completing every M3 gate first, but scheduler benchmarks must use **simulation + recorded traces** until multi-world live path exists.

## Scheduler-related code classification

| Component | Classification | Notes |
|-----------|----------------|-------|
| `ghostrange_scheduler.schedule()` (v1) | **IMPLEMENTED** | Per-task `SchedulerDecisionV1`; budget, deps, stopping, straggler hint (p90×1.5) |
| `priority.py`, `stopping.py`, `cost.py` | **HEURISTIC** | Documented formulas; placeholder rate card for some tiers |
| `resource_selection.py` | **PARTIAL** | CPU/GPU from profile labels; **GPU_NOT_JUSTIFIED** path exists |
| `parallelism.py` | **HEURISTIC** | Cap-based parallelism |
| `benchmarks.py` (ALL_CASES) | **UNTESTED** in cloud | Unit-tested decision fixtures only |
| `SchedulingContextV2` / `SchedulerDecisionV2` | **STUB** | Pydantic only; **no runtime consumer** |
| Critical path / slack | **STUB** | Not in v1 scheduler |
| Queue pressure / scale-out/in | **STUB** | Reason codes exist; **no autoscale loop** in API/runtime |
| Speculation duplicate/cancel | **PARTIAL** | Policy flags on task; **no duplicate-task orchestration** |
| Fragmentation metrics | **STUB** | Not implemented |
| Adaptive inference (`ReasoningBudgetV1`) | **STUB** | Not implemented |
| `EvidenceValueModel` (optional exploration) | **PARTIAL** | VoI stopping in v1 for running tasks |
| Scheduler simulator / traces | **STUB** | M2 scheduler self-benchmarks only |
| API `GET /scheduler/*` | **MISSING** | No inspection endpoints |
| Execution UI speculation/split | **FIXTURE_ONLY** | Renders events; not tied to v3 decisions |
| Live Vultr calibration | **UNTESTED** | `vultr-control` partial; no M4 latency store |

## Blocking M4 (must address in Wave 1–2)

1. **Contract freeze** — `SchedulingContextV3`, `SchedulingPlanV3`, profiles, models, traces.  
2. **Plan entrypoint** — multi-action `plan()` vs single-task `schedule()`.  
3. **Simulator + baselines** — STATIC_*, FIRST_FIT, GHOSTSCHEDULER_V3 on same traces.  
4. **Config surface** — `config/ghostscheduler-v3.yaml` (no buried magic constants).  
5. **Decision persistence** — wire to events or API for UI + replay.

## Ready for M4

- Explainable `SchedulerDecisionV1` + expanded `ReasonCode` vocabulary (M3 codes).  
- `ClusterStateV1`, `WorldStateV1`, duration stats, budget state.  
- Deterministic unit-test culture (115 scheduler tests).  
- Execution-mode 3D components (critical path visuals = extend, not new tab).

## Non-goals (M4 prompt)

- RL / policy networks  
- LLM chooses infrastructure  
- New primary UI tabs  
- Cyber feature creep unrelated to scheduling
