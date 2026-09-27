# M18 — Self-improvement synthesis

## Self-improving agents survey (~2026)

| Field | Content |
|-------|---------|
| PROBLEM | When can agents improve from experience? |
| UPDATE TARGET | Foundation model **vs** scaffold (prompts, memory, tools, control) |
| GHOSTRANGE TRANSLATION | M18 v1 = **scaffold only** (runtime estimator), not LLM fine-tune |
| WHAT WE REJECT | "Recursive self-improvement" marketing |
| FORGETTING RISK | High if retraining on latest only |

## Metacognitive / self-assessment (ICML 2025 lineage)

| Field | Content |
|-------|---------|
| PROBLEM | Assessment, planning what to learn, and evaluation are separate |
| GHOSTRANGE TRANSLATION | `EvolutionPlanner` + `CapabilitySelfAssessmentV1` |
| WHAT WE ADOPT | Dimensional metrics, bottleneck attribution |

## Continual learning / catastrophic forgetting

| Field | Content |
|-------|---------|
| PROBLEM | New data degrades old task performance |
| GHOSTRANGE TRANSLATION | Old-workload holdout + `ForgettingReportV1` |
| SAFETY MECHANISM | Regression gate before promotion |

## Drift (representation, workload, provider)

| Field | Content |
|-------|---------|
| PROBLEM | Non-stationary environment |
| GHOSTRANGE TRANSLATION | `DriftSignalV1` triggers **evaluation**, not auto-retrain |
| WHAT WE MUST NOT CLAIM | Drift detection solved |

## Shadow / canary / champion–challenger

| Field | Content |
|-------|---------|
| ENFORCEMENT MODEL | Challenger observes; champion acts until permitted promotion |
| GHOSTRANGE TRANSLATION | Shadow UI + promotion via GhostShield |

## Safe policy improvement / off-policy evaluation

| Field | Content |
|-------|---------|
| LIMITATIONS | Counterfactual outcomes often **OFF_POLICY_UNKNOWN** |
| GHOSTRANGE TRANSLATION | `EvolutionReplayEngine.counterfactual_note` |

## What we must not claim

- Continual learning solved
- GhostRange "rewrites itself"
- Candidates self-deploy
- Learning from unverified experience
