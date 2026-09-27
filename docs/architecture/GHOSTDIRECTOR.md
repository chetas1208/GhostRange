# GhostDirector (M9)

**GhostDirector** chooses **what experiment** to run next. **GhostScheduler** chooses **how** approved work uses compute. They must not merge.

```
InvestigationKnowledgeStateV1
        → generate + validate candidates
        → ExperimentUtilityV1 / AcquisitionScoreV1
        → ExperimentPortfolioV1 + DirectorDecisionV1
        → ExperimentExecutionDAGV1  ──handoff──▶ GhostScheduler
        → ExperimentObservationV1
        → knowledge update (+ SurpriseObservationV1)
```

## Uncertainty

`BeliefLevel` (UNKNOWN/LOW/MEDIUM/HIGH) — no fake percentage confidence unless statistically grounded.

## Hypotheses

`InvestigationHypothesisV1` is separate from incident `HypothesisV1` in `hypothesis.py`.

## Policies (benchmark)

`FIXED_SCRIPT`, `RANDOM_SAFE`, `GREEDY_INFORMATION`, `GREEDY_DECISION_VALUE`, `GHOSTDIRECTOR_V1`.

## Package

`packages/ghostdirector` — `GhostDirectorSimulator` for in-process campaigns.

## M8 integration

`RUN_COUNTEREXAMPLE_SEARCH` is one `ExperimentOperatorKind`; Director may select it when VoI is high.

## Provenance

Director decisions with pre-execution utility snapshots → GhostLedger (wiring pending).
