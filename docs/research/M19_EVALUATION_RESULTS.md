# M19 evaluation results (simulated arena)

## Required negative case — **demonstrated**

| Field | Value |
|-------|-------|
| Candidate | stopping-policy:v6 (`fast_premature`) |
| Baseline | stopping-policy:v5 |
| Visible regression | PASS (sim) |
| Hidden generalization / process | **FAIL** — premature branch cancel |
| Cost delta | -21% |
| Qualification | **NOT_QUALIFIED** |

## Positive qualification case — **demonstrated**

| Field | Value |
|-------|-------|
| Candidate | runtime-estimator:v7 (`qualified`) |
| Baseline | runtime-estimator:v6 |
| Qualification | **QUALIFIED** |
| Cost delta | -8.4% (sim report field) |

## Live Vultr

**LIVE_ARENA_NOT_RUN**

## Reproducibility

Sim runs: fixed seeds in `ArenaHiddenBundleV1`; policies deterministic in `simulate_candidate_behavior`.
