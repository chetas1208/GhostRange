# M4 Final — (in progress)

GhostScheduler Intelligence campaign started **2026-09-26**. This document will be completed when prompt §87 gate passes.

## Wave 0–1 delivered (lead integration)

- `docs/milestones/M4_AUDIT.md`
- `docs/milestones/M4_COORDINATION.md` (26 workstreams)
- `docs/research/M4_SCHEDULING_SYNTHESIS.md`
- Contract freeze: `packages/contracts/ghostrange_contracts/scheduler_v3.py` + `packages/contracts/scheduler/`
- `config/ghostscheduler-v3.yaml`
- `ghostrange_scheduler.v3.plan()` + simulator skeleton
- `docs/architecture/GHOSTSCHEDULER_V3.md`

## Not yet complete

- Full benchmark matrix vs STATIC_* / COST_MIN with published `M4_BENCHMARK_REPORT.md`
- API `GET /scheduler/*`
- Live Vultr calibration artifacts
- Execution UI wired to V3 plan actions
- Straggler/speculation/preemption live loops
- M3 multiverse live path (feeds realistic traces)

See `M4_COORDINATION.md` for agent status.
