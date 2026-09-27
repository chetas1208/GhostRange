# Promotion model (M11)

## Flow

```text
Verified remediation (Fix B.2)
  → GhostGate.prepare()
  → ProductionChangeCandidateV1
  → dimensional PromotionReadinessV1
  → human ApprovalRequestV1 (hash-bound)
  → GhostPromotionBundleV1 export
  → external deployment (out of scope)
```

## Key types

| Type | Role |
|------|------|
| `TestedProductionDeltaV1` | Tested twin actions vs proposed production actions |
| `ChangeEquivalenceReportV1` | Per-dimension EXACT / MATERIAL_DIFFERENCE / … |
| `PromotionReadinessV1` | Gate dimensions — no single score |
| `ChangeRiskProfileV1` | Multidimensional risk (identity, data, blast radius, …) |
| `DeploymentStrategyV1` | Recommended rollout (often CANARY for identity changes) |
| `RollbackPlanV1` + `RollbackStatus` | Plan + in-range drill status |
| `PostDeploymentVerificationPlanV1` | Operator checklist after prod deploy |
| `ApprovalDecisionV1` | Human/service only — binds to `change_candidate_hash` |

## Golden path integration

`POST /v1/golden-path/runs?with_promotion=true` seals M10 evidence then calls GhostGate with the same adversarial report and `bundle_digest` as evidence root.

## Idempotency

Repeated prepare with the same `(experiment_id, source_revision_id, twin_revision_id, evidence_root_digest, remediation_id)` returns the same candidate.
