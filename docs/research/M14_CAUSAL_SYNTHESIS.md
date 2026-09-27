# M14 Causal Synthesis

## Adopt

- **Pearl hierarchy**: observe vs intervene vs counterfactual — separate in API/contracts
- **Transportability** (Bareinboim/Pearl): source/target differences explicit; partial transport
- **Testing generalizability** (2025): predictive fit ≠ causal generalization — benchmark uses hidden SCM evaluator
- **Negative transfer** (2025 transport+TL): structural similarity baseline vs causal transport in `benchmark_m14.py`

## Reject

- LLM as causal oracle
- Single DAG forced when confounded (latent → NOT_IDENTIFIABLE benchmarks planned)
- NOTEARS on all problems without assumption match

## GhostRange advantage

Counterfactual worlds materialized as disposable ranges (`COUNTERFACTUAL_CACHE_BEFORE_REFRESH` intervention kind).
