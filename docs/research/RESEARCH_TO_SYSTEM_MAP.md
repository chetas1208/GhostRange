# Research-to-System Map

This map connects an architectural idea to code and an evaluation artifact. It deliberately distinguishes a documented design bet from a live production result.

| Concept / research theme | Design decision | Implementation | Evaluation or evidence | Boundary |
| --- | --- | --- | --- | --- |
| Isolated multi-host cyber ranges | Test authorized hypotheses outside production | `packages/range-compiler`, `packages/range-runtime`, `ranges/ghostrange-auth-lab-v1` | Range compiler and mock golden-path tests | Live isolated range proof is not complete in M20 |
| Digital twins and world lineage | Represent a system as a reproducible, disposable investigation world | `packages/range-compiler`, `packages/contracts`, `apps/api/ghostrange_api/multiverse_fork.py` | M6 drift tests, M3 forking docs, UI Multiverse state | Fidelity is scenario-bounded; not universal production equivalence |
| Long-horizon experiment design | Choose discriminating experiments from hypotheses and evidence | `packages/ghostdirector`, `docs/architecture/GHOSTDIRECTOR.md` | Director package tests and golden-path simulator | Director is simulator-backed in the canonical campaign |
| Adaptive compute | Rank work by evidence value, uncertainty, dependency criticality, and marginal cost | `packages/scheduler`, `packages/scheduler/ghostrange_scheduler/v3`, `docs/research/ADAPTIVE_COMPUTE.md` | Scheduler unit tests, benchmark fixtures, plan-preview route | Live provider placement remains gated |
| Provider billing quanta | Treat a new worker as at least one provider billing quantum | `packages/cost/ghostrange_cost/compute_billing.py`, `vultr_policy.py` | Cost acceptance tests and scheduler cost tests | Provider invoice-level campaign totals are unavailable through the current API |
| Evidence provenance | Keep claims traceable to artifacts, events, tasks, workers, and source revisions | `packages/evidence`, `packages/ghostledger`, `apps/api/ghostrange_api/artifact_registry.py` | Ledger seal/verify tests and evidence contracts | End-to-end live campaign provenance is not complete |
| Adversarial verification | Attempt counterexamples after a candidate remediation appears successful | `packages/adversarial-verifier`, `packages/ghostarena` | Adversarial package tests, M8/M19 simulator evidence | Arena is an independent simulator, not production certification |
| Causal intervention | Use interventions and counterfactual queries to distinguish mechanisms | `packages/ghostcausal`, `/v1/causal/*` routes | M14 simulator tests and causal API tests | No live causal campaign is claimed |
| Safety and human authority | Typed effects pass through GhostShield and promotion boundaries | `packages/ghostshield`, `apps/api/ghostrange_api/shielded_vultr_adapter.py`, `packages/ghostgate` | Bypass, enforcement, and promotion tests | Live worker end-to-end verification remains open |
| Federated defensive priors | Share sanitized, policy-checked knowledge rather than raw evidence | `packages/ghostmesh`, `docs/security/GHOSTMESH_*` | Five-node logical harness and Mesh API tests | Live multi-Vultr mesh is not run |
| Independent evaluation | Keep hidden Arena truth outside runtime/learner paths | `packages/ghostarena`, `docs/security/ARENA_RANGE_BOUNDARY.md` | Arena release-report simulator and hidden-data boundary docs | Current Arena result is simulated |
| Human-readable tactical observability | Keep 3D for relationships and DOM for precision/accessibility | `apps/web/src`, `packages/ui-3d`, `docs/ui/*` | Frontend tests, Playwright specs, screenshot acceptance spec | Human visual/tour sign-off remains pending |

## Interpretation rule

The implementation and evidence columns answer “what exists and what was tested.” They do not turn a simulator into a live integration or an experiment result into a production safety guarantee. The release-facing status is maintained in [the reality matrix](../release/REALITY_MATRIX.md).

