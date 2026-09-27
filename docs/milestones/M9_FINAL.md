# M9 Final — GhostDirector (in progress)

## What is GhostDirector?

The experiment-**design** layer: given `InvestigationKnowledgeStateV1`, propose safe experiments, score them, select a portfolio, hand off an `ExperimentExecutionDAGV1` to GhostScheduler, observe, update knowledge, stop honestly.

## vs GhostScheduler

| GhostDirector | GhostScheduler |
|---------------|----------------|
| WHAT to test | HOW to run approved tasks |
| Hypothesis discrimination | Worker placement, scale, cost |
| `ExperimentProposalV1` | `SchedulingPlanV3` |

## Uncertainty

`UncertaintyItemV1` + `BeliefLevel` — qualitative unless a real posterior exists.

## Experiment generation

Rule templates in `generate.py`; Vultr Serverless structured drafts **stub only**.

## Acquisition

`AcquisitionScoreV1` combines information, decision value, representativeness, robustness, minus cost — not pure EIG.

## Surprise / misspecification

`detect_surprise` can spawn new `InvestigationHypothesisV1` when observations mispredict active set.

## Benchmarks

`GhostDirectorSimulator` + `benchmarks/m9/ground_truth/auth_incident.json` (harness-only).

## Gate status

§145 mostly **open**: API, UI layers, GhostLedger director bundle, live Vultr campaign, full policy curves, security matrix, E2E.

## Ready for M10

Product integration milestone: wire M2–M9 golden path, remove mocks, end-to-end demo with cleanup.
