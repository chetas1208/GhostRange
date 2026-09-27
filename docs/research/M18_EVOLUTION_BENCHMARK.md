# M18 evolution benchmark (initial)

Baselines to compare (runtime estimator):

| Baseline | Description |
|----------|-------------|
| NO_UPDATE | Keep champion |
| STATIC_M15 | `M15RuntimeEstimatorChampion` inflation |
| RETRAIN_LATEST_ONLY | Train on last N only (forgetting probe) |
| FULL_HISTORY_RETRAIN | All eligible history |
| GHOSTEVOLVE | Temporal split + regression + promotion gates |

Metrics: MAE, p95 error, old/new holdout, slice regression, unsafe promotion rate (target 0), training/evaluation USD (TBD).

Artifacts dir: `artifacts/benchmarks/m18/` (populate on benchmark runs).
