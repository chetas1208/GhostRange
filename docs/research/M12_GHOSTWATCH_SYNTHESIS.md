# M12 GhostWatch — Research Synthesis

## Argo Rollouts / Flagger (progressive delivery)

| Source | Problem | GhostRange translation |
|--------|---------|------------------------|
| Argo Rollouts | Staged canary + analysis + abort | `DeploymentExecutorAdapterV1` capability model; **observe** stage/metrics; optional **preauthorized** pause/rollback |
| Flagger | Metric thresholds → promote/abort | `CanaryAnalysisV1` multi-signal gates; debounce |

**Adopt:** Normalized stages, deterministic gates, explicit rollback triggers.  
**Reject:** GhostRange owning the Kubernetes controller.  
**Must not claim:** Simulator success = production validation.

## OpenFeature (feature flags)

**Adopt:** `FeatureFlagAdapterV1` interface — `OBSERVE` + `SET_APPROVED_VALUE` only when bundle lists exact flag/value.  
**Reject:** Arbitrary flag creation or model-chosen values.

## SRE / runtime verification

**Adopt:** Missing data ≠ PASS; baselines; error budgets as **approved thresholds** in bundle.  
**Reject:** LLM-invented thresholds mid-rollout.
