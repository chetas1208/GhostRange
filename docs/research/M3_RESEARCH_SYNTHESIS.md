# M3 research synthesis (living)

Maps external ideas → GhostRange M3 implementation. **Implementation beats documentation** — this file tracks adoption decisions.

| Topic | Source / claim | Limitation | GhostRange translation | Owner agent |
|-------|----------------|------------|------------------------|-------------|
| Fork reproducibility | Vultr instance templates bundle plan, image, user-data, VPC | Not instant snapshot create | Strategy A in ADR-M3 | 04 |
| Parallel hypothesis testing | Multi-armed bandit / batch testing (general IR) | Needs fair test suites | `VerificationSuiteV1` + `WorldEvaluationV1` | 10 |
| Critical-path scheduling | CPM on DAG | Cloud noise | `packages/execution-graph` + Agent 14 | 14 |
| Autoscaling hysteresis | Queue-based scale (K8s HPA pattern) | Over-flap without cooldown | Agent 15 min lifetime + thresholds | 15 |
| Straggler mitigation | Speculative duplicate tasks (MapReduce stragglers) | Wasted compute | Agent 16 + cost tracking | 16 |
| Value of information | Stop when marginal evidence gain low | Must not skip mandatory tests | Agent 17 optional exploration only | 17 |
| Branch priority heuristic | Risk × uncertainty × gain / cost | Not ML-calibrated yet | Agent 13 + benchmark baselines | 13, 23 |

## Benchmark thesis (M3)

> Branch-aware scheduling vs static serial / static parallel / fixed pool on verification coverage, wall time, and compute waste.

Baselines stored under `artifacts/benchmarks/m3/`. Negative results are valid.

## M4 pointer

After M3: richer cost models, heterogeneous placement, stronger speculation, workload profiling — **GhostScheduler Intelligence** milestone.
