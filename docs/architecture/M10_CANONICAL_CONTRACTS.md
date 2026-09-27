# M10 Canonical Contracts (freeze after Wave 0)

Do not introduce V4/V5 without adapter. Prefer adapters at integration boundaries.

| Domain | Canonical type | Package | Notes |
|--------|----------------|---------|-------|
| Range spec | `RangeSpecV1` (runtime) + `RangeSpecV2` (compiler output) | contracts | Adapter: compile → V1 for runtime |
| World | `WorldV1` / `WorldForkV2` | contracts | M3 fork not fully wired |
| Task / execution | `TaskV1`, `ExecutionGraphV1` | contracts | |
| Evidence | `EvidenceV1`, `ClaimV1`, `ArtifactV1` | contracts | |
| Scheduler (M2 API) | `SchedulerDecisionV1` + events | contracts / events | |
| Scheduler (compute) | `SchedulingPlanV3` | scheduler_v3 | Golden path uses V3 for new work |
| Director | `DirectorDecisionV1`, `ExperimentProposalV1` | ghostdirector_m9 | |
| Adversarial | `CounterexampleV1`, `AdversarialSearchPlanV1` | adversarial_m8 | |
| Living twin | `TwinRevisionV1`, `ClaimValidityV1` | living_twin_m6 | |
| Ledger | `ExperimentManifestV1`, `GhostBundleV1` | ghostledger_m7 | |
| Incident hypothesis | `HypothesisV1` | hypothesis.py | Remediation worlds |
| Investigation hypothesis | `InvestigationHypothesisV1` | ghostdirector_m9 | Director only |

## Event naming

Prefer existing registry in `packages/events/ghostrange_events/`. M8/M9 names live in `adversarial_events.py`, `director_events.py` — register in gateway when emitting from golden path.
