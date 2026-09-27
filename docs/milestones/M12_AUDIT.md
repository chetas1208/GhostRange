# M12 Audit — Wave 0 (corrected for honest M11 inheritance)

**M11 Agent 32: NO-GO** — M12 must not pretend otherwise.

## M11 carry-forward gate (§2)

| M11 blocker | Status in repo | Classification |
|-------------|----------------|----------------|
| Exact-patch recompile loop | `verify_proposed_patch()` + `POST .../verify-exact-patch` | **REAL_PARTIAL** — local Range Compiler only; **not** live Vultr twin verify |
| Live Vultr promotion/rollback worlds | Not run | **INHERITED_M11_BLOCKER** — simulator only |
| GhostLedger promotion lineage | `InMemoryPromotionLedger` + campaign SSE hooks | **REAL_PARTIAL** — not sealed M7 bundle |
| Live M11 screenshots | Not captured | **INHERITED_M11_BLOCKER** |
| Richer approval evidence UI | PromotionPanel + patch preview | **REAL_PARTIAL** |
| Agent 32 GO | NO-GO | **INHERITED_M11_BLOCKER** |

**Gate decision:** M12 proceeds on **SIMULATED_ROLLOUT** + **LOCAL COMPILE** paths; labels must not claim M11 live completion.

## M11 artifacts GhostWatch depends on

| Artifact | Classification |
|----------|----------------|
| `change_candidate_hash` + `ApprovalDecisionV1` | **REAL_VERIFIED** |
| `GhostPromotionBundleV1` | **REAL_VERIFIED** |
| `ExternalDeploymentRecordV1` | **REAL_VERIFIED** — ingress at `POST /v1/ghostwatch/campaigns/{id}/external-record` |
| `DeploymentStrategyV1` / rollback on candidate | **REAL_PARTIAL** (plan metadata) |

## M12 GhostWatch (this milestone slice)

| Component | Classification |
|-----------|----------------|
| Authority default OBSERVE_ONLY | **REAL_VERIFIED** |
| ProductionRolloutSimulator | **REAL_VERIFIED** — labeled SIMULATED |
| Multi-dim conformance | **REAL_VERIFIED** |
| `TwinPredictionV1` before observation | **REAL_VERIFIED** |
| `config/ghostwatch-policy.yaml` | **REAL_VERIFIED** |
| Argo Rollouts adapter | **NOT DONE** |
| Prometheus/OTEL live adapter | **NOT DONE** |
| Living Twin write-back | **NOT DONE** |
| Agent 38 GO | **NO-GO** |

## Benchmark

`scripts/benchmark_m12.py` — unsafe_advance_count=0 on current simulator corpus (**SIMULATED**, not production).
