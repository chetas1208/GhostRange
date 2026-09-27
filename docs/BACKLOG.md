# GhostRange backlog disposition

**Reconciled:** 2026-09-27 UTC
**Scope:** the original 54-item M2–M10 backlog, checked against this checkout,
the local release matrix, and the published `main` branch.

This is a disposition ledger, not a promise that research milestones are
production-ready. `DONE` means the local implementation and tests support the
claim. `PARTIAL` means a meaningful slice exists but an integration or proof
surface remains. `BLOCKED` requires an external action or capability that is
not available to this checkout. `DEFERRED` is intentionally outside the
research-prototype release gate. No simulated result is promoted to `LIVE`.

## Repository and M2

| # | Workstream | Disposition | Evidence / remaining gate |
| ---: | --- | --- | --- |
| 1 | First git baseline | **DONE** | Public `main` published at `github.com/chetas1208/GhostRange`. |
| 2 | Refresh `Progress.md` | **DONE** | `Progress.md`, `docs/OVERNIGHT_STATE.md`. |
| 3 | Rename duplicate scheduler test | **DONE** | Root test matrix passes. |
| 4 | Postgres EventGateway API default | **PARTIAL** | Durable gateway is selected when Postgres + Redis are configured; memory mode remains the safe local default. |
| 5 | `INTEGRATION_STATUS.md` maintenance | **DONE** | Reconciled by the M20 audit and release matrix. |
| 6 | Live Vultr one-world E2E | **BLOCKED** | Provider read-only call is rejected by the current egress-IP ACL; no billable resource was created. |
| 7 | Policy execution events | **PARTIAL** | Typed gateway and execution contracts exist; full durable policy-event audit is not yet wired. |
| 8 | Serverless inference planner | **DONE** | Inference pool, budget caps, costing, routes, and tests are present. |
| 9 | `packages/adversary-adapter` | **PARTIAL** | Caldera client and safety tests exist; live adapter proof is not claimed. |
| 10 | `packages/execution-graph` runtime | **DONE** | DAG validation/topological ordering and cycle tests pass. |

## M3 multiverse

| # | Workstream | Disposition | Evidence / remaining gate |
| ---: | --- | --- | --- |
| 11 | Fork orchestrator (3 worlds) | **PARTIAL** | Mock/API fork path and events exist; live multi-world provisioning is not proven. |
| 12 | GhostScheduler V2 runtime | **DONE** | Current implementation is Scheduler V3; guardrails, dry-check, preview, worker, and list routes are present. |
| 13 | Attack replay and per-world regression | **PARTIAL** | GhostWatch replay/simulation primitives exist; a complete multi-world replay corpus remains. |
| 14 | Evidence namespace isolation | **PARTIAL** | Evidence/provenance models exist; cross-world durable isolation needs a database acceptance run. |
| 15 | Event idempotency | **DONE** | Event-store ordering/idempotency and duplicate-path tests pass locally. |
| 16 | Live multiverse UI | **PARTIAL** | Three-mode tactical UI, fork events, and replay semantics exist; live backend wiring is pending deployment. |
| 17 | M3 benchmarks | **DEFERRED** | Research benchmark expansion is not required for the M20 prototype gate. |
| 18 | M3 live screenshots | **BLOCKED** | Requires compatible browser dependencies and human visual review. |
| 19 | M3 final gate | **PARTIAL** | Historical M3 gate was never a production certification; current truth is captured in `docs/milestones/M20_OVERNIGHT_AUDIT.md`. |
| 20 | Multi-world orphan scanner | **PARTIAL** | Ownership/tagged-worker scans exist; full multi-world live cleanup proof is blocked with item 6. |

## M4 scheduler

| # | Workstream | Disposition | Evidence / remaining gate |
| ---: | --- | --- | --- |
| 21 | Straggler and speculation modules | **PARTIAL** | Scheduler primitives and simulator exist; production execution policy is not enabled. |
| 22 | Autoscale and fragmentation | **PARTIAL** | V3 placement/guardrail plan exists; live calibration remains open. |
| 23 | Adaptive inference budget | **DONE** | Inference concurrency ceiling, budget reservation, and token-cost tests pass. |
| 24 | Benchmark matrix | **DEFERRED** | No synthetic performance number is presented as measured production behavior. |
| 25 | `GET /scheduler/*` API | **DONE** | Guardrails, compute dry-check, workers, and preview surfaces are implemented. |
| 26 | Execution UI from V3 decisions | **PARTIAL** | Director/Scheduler strip is present; full live decision stream awaits deployment. |
| 27 | Vultr calibration | **BLOCKED** | Requires an ACL-allowed, explicitly authorized provider run. |
| 28 | M4 benchmark report | **PARTIAL** | Research synthesis exists; current evidence matrix intentionally records missing live measurements. |
| 29 | M4 final gate | **BLOCKED** | Depends on live calibration and benchmark evidence, not code alone. |
| 30 | Scheduler decision persistence | **PARTIAL** | Durable hooks and operation timing persistence exist; restart acceptance remains outstanding. |

## M5 compiler

| # | Workstream | Disposition | Evidence / remaining gate |
| ---: | --- | --- | --- |
| 31 | Live provision from RangeSpecV2 | **BLOCKED** | Control-plane provider path exists; live provisioning is gated by Vultr authorization and safety approval. |
| 32 | Multi-source merge | **PARTIAL** | Compose, Kubernetes, and Terraform importers exist; merge/conflict UX is not complete. |
| 33 | `ghostrange.yaml` blueprint | **PARTIAL** | Twin blueprint and compiler contracts exist; a stable user-facing blueprint format is not frozen. |
| 34 | External stub and network safety | **PARTIAL** | Sanitization and safety boundaries exist; external integration proof remains simulated. |
| 35 | Behavioral invariant runtime | **PARTIAL** | Invariant/verification components exist; end-to-end runtime enforcement is incomplete. |
| 36 | SourceShadow UI | **DEFERRED** | Product UI expansion is not required for the current three-mode prototype gate. |
| 37 | Compiler API and events | **PARTIAL** | Compiler pipeline and golden-path integration exist; repository intake still returns a derived model only. |
| 38 | M5 benchmarks | **DEFERRED** | Requires a controlled corpus and reproducible benchmark publication. |
| 39 | Compiled world to verification E2E | **PARTIAL** | Local compiler/golden path is covered; live compiled-world proof is not. |
| 40 | M5 final gate | **BLOCKED** | Depends on items 31 and 39 live evidence. |

## M6 living twin

| # | Workstream | Disposition | Evidence / remaining gate |
| ---: | --- | --- | --- |
| 41 | Source watch | **PARTIAL** | Living-twin revision/diff engine exists; continuous source watching is not enabled. |
| 42 | Revision API | **OPEN** | Revision models exist, but no supported public `POST .../revisions` route is shipped. |
| 43 | Drift domain events | **PARTIAL** | Drift classification and revalidation contracts exist; durable event emission remains. |
| 44 | Assumption/evidence persistence | **PARTIAL** | Provenance models and artifact hooks exist; restart acceptance remains. |
| 45 | Scheduler revalidation tasks | **PARTIAL** | Revalidation decision logic exists; scheduler task integration is incomplete. |
| 46 | Multiverse drift visuals | **DEFERRED** | Requires the complete live drift event stream and visual acceptance. |
| 47 | Evidence staleness UI | **PARTIAL** | Staleness models and evidence UI states exist; live revision wiring remains. |
| 48 | Mutation goldens | **PARTIAL** | Drift fixtures and mutation tests exist; full corpus is not complete. |
| 49 | M6 benchmarks | **DEFERRED** | Research measurement work, not a prerequisite for the local prototype gate. |
| 50 | M6 final gate and live experiment | **BLOCKED** | Requires authorized live infrastructure and a completed revision API. |

## M10 integration

| # | Workstream | Disposition | Evidence / remaining gate |
| ---: | --- | --- | --- |
| 51 | Golden-path SSE events | **DONE** | Golden-path event tests and mock campaign pass. |
| 52 | Full local test command | **DONE** | `make test`, `make demo`, and the release matrix are wired. |
| 53 | Live golden path and lease | **PARTIAL** | Mock path is verified; live worker proof is blocked by provider ACL and deployment drift. |
| 54 | Agent 40 GO gate | **BLOCKED** | Correct result is `NO-GO` until live deployment, worker proof, database restart, and human UI review are complete. |

## Closure summary

- **DONE:** 12 items are locally implemented and validated.
- **PARTIAL:** 27 items have a meaningful implementation but missing integration or proof.
- **BLOCKED:** 8 items require external infrastructure, authorization, or human review.
- **DEFERRED/OPEN:** 7 items remain intentionally outside this prototype release gate.

The release decision and external evidence are maintained in
[`docs/release/REALITY_MATRIX.md`](release/REALITY_MATRIX.md),
[`docs/release/RELEASE_CHECKLIST.md`](release/RELEASE_CHECKLIST.md), and
[`docs/OVERNIGHT_HANDOFF.md`](OVERNIGHT_HANDOFF.md).
