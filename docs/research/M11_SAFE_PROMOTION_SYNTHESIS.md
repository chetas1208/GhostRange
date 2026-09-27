# M11 Safe Promotion — Research Synthesis

## Progressive delivery / canary (Google SRE, LaunchDarkly patterns)

| Field | Detail |
|-------|--------|
| Problem | Reduce blast radius of production change |
| GhostRange | `CanaryPlanV1` as **plan only** — not traffic routing |
| Must not claim | Simulated canary = production canary success |

## Blue/green & rolling

| GhostRange | `DeploymentStrategyV1` blueprint; no prod provisioning |

## Rollback (SRE, change management)

| GhostRange | `RollbackPlanV1` + disposable-world **ROLLBACK_TEST** simulation status |
| Must not claim | Twin rollback = guaranteed prod rollback |

## Expand-contract (schema migrations)

| GhostRange | Flag `IRREVERSIBLE` / `MANUAL_RECOVERY_REQUIRED` on data deltas |

## Policy-as-code / human gate

| GhostRange | `ApprovalPolicyV1`; human identity only in `ApprovalDecisionV1` |

## Rejected for M11

- Autonomous production apply
- GitHub Actions triggers (user rule)
- Opaque “deployability %”
