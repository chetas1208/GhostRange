# GhostCausal

```
Observations → candidate graph (hypothesized)
       → Director discrimination interventions
       → Scheduler parallel control/intervention worlds
       → graph update (INTERVENTION_SUPPORTED / REFUTED)
       → counterfactual query → optional counterfactual world
       → transportability query (vs Mesh structural prior)
```

Code: `packages/ghostcausal/`, contracts `ghostcausal_m14.py`, API `/v1/causal/*`.

Ground truth SCM: **evaluator/benchmark only** — `GhostCausalSimulator._EvaluatorGroundTruth` not used by `CausalInvestigationEngine`.
