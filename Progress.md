# Progress — GhostRange (M1–M20)

**Updated:** 2026-09-27 (tactical UI + cost accounting Phase 2)

**Overnight campaign snapshot:** see [docs/OVERNIGHT_STATE.md](docs/OVERNIGHT_STATE.md), [M20 overnight audit](docs/milestones/M20_OVERNIGHT_AUDIT.md), and [release reality matrix](docs/release/REALITY_MATRIX.md). Local release gates pass; final recommendation remains `NO-SHIP` because the public deployment is stale, live Compute proof is ACL-blocked, and publication/UI human gates remain open.

## Summary

| Milestone | Status |
|-----------|--------|
| M1 UI shell | Done (fixture + 3 tabs) |
| M2 one-world API | Mock E2E pass |
| M3 multiverse | Partial (fork API events) |
| M4 GhostScheduler V3 | Package + plan-preview API |
| M5 Range compiler | Compose pipeline + golden path compile |
| M6 Living twin | Drift engine unit tests |
| M7 GhostLedger | Seal + offline verify |
| M8 Adversarial verifier | In-process search |
| M9 GhostDirector | Simulator + golden path |
| M10 One system | Mock golden path + integration docs (**NO-GO** release) |
| M11 GhostGate | Contracts + promotion API (**Agent 32 NO-GO**) |
| M12 GhostWatch | Simulator + conformance (**Agent 38 NO-GO**) |
| M13 GhostMesh | 5-node harness + Mesh API (**Agent 40 NO-GO**, simulated) |
| M14 GhostCausal | SCM simulator + transport (**Agent 42 NO-GO**, simulated) |
| M15–M16 | Scheduler/runtime packages (**partial NO-GO**) |
| M17 GhostShield | ENFORCE partial (**NO-GO** bypass) |
| M18 GhostEvolve | Experience + Arena promotion gate (**NO-GO**) |
| M19 GhostArena | Independent eval sim (**NO-GO**) |
| M20 GhostRange One | Unified campaign API + release scripts (**NO-SHIP**) |

## Tests

Run: `make test` or `scripts/run-all-tests.sh`

~160+ Python tests across packages + API; web typecheck/unit via npm.

## Golden path (mock)

```bash
curl -X POST http://127.0.0.1:8000/v1/golden-path/runs
```

Emits: compile → director → scheduler → adversarial → ledger (+ SSE events).

## Live

Requires `GHOSTRANGE_LIVE=true` + `VULTR_API_KEY` + `scripts/live_resource_lease.py`.

## Git

Initial public baseline is being prepared on `main`; historical milestone audits may still refer to the pre-publication uncommitted tree.

## Tactical UI + cost (engineering)

- Tactical UI: `docs/ui/TACTICAL_UI_FINAL.md`
- Cost accounting: `docs/milestones/M20_COST_ACCOUNTING_FINAL.md`, `docs/architecture/COST_ACCOUNTING_AUDIT.md`

## Docs

- Integration: `docs/INTEGRATION_STATUS.md`
- Backlog: `docs/BACKLOG.md`
- Operations: `docs/OPERATIONS.md`
