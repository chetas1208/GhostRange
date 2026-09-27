# M9 Coordination — GhostDirector (36 specialists)

Lead: architecture, contract freeze, integration, safety, benchmarks, release gate.

**GhostDirector ≠ GhostScheduler** — Director selects experiments; Scheduler allocates compute to approved DAG.

## Contract freeze

**Wave 1:** `InvestigationKnowledgeStateV1`, `UncertaintyItemV1`, `InvestigationHypothesisV1`, `HypothesisGraphV1`, `ExperimentProposalV1`, `ExperimentObservationV1`  
**Wave 2:** `ExperimentUtilityV1`, `AcquisitionScoreV1`, `EvidenceConflictV1`  
**Wave 4:** `ExperimentPortfolioV1`, `ExperimentCampaignBudgetV1`, `DirectorDecisionV1`, `SurpriseObservationV1`

| agent_id | mission | owned_paths | status |
|----------|---------|-------------|--------|
| 01 | M9 audit | `M9_AUDIT.md` | done |
| 02 | Experiment design research | `M9_EXPERIMENT_DESIGN_SYNTHESIS.md` | done |
| 03 | Knowledge state | `ghostdirector_m9.py` | done |
| 04 | Uncertainty model | `ghostdirector_m9.py` | done |
| 05 | Hypothesis graph | `ghostdirector_m9.py` | done |
| 06 | Experiment contracts | `ghostdirector_m9.py` | done |
| 07 | Experiment operators | `operators.py` | done |
| 08 | Expected outcomes | `expected_outcomes.py` | done |
| 09 | Information gain | `utility.py` | done |
| 10 | Value of information | `utility.py` | done |
| 11 | Representativeness | `utility.py` | done |
| 12 | Robust acquisition | `acquisition.py` | done |
| 13 | Rule candidate gen | `generate.py` | done |
| 14 | Model-guided (Vultr) | `model_proposals.py` stub | partial |
| 15 | Candidate validation | `validate.py` | done |
| 16 | Deduplication | `dedupe.py` | done |
| 17 | Experiment memory | `memory.py` | done |
| 18 | Portfolio optimization | `portfolio.py` | done |
| 19 | Diversity | `portfolio.py` | partial |
| 20 | Stopping policy | `stopping.py` | done |
| 21 | Misspecification / surprise | `surprise.py` | done |
| 22 | Evidence conflict | `conflicts.py` | done |
| 23 | Causal research | synthesis doc | done |
| 24 | Replication | `replication.py` stub | partial |
| 25 | Scheduler bridge | `scheduler_bridge.py` | done |
| 26 | Cost estimation | `cost_estimate.py` | done |
| 27 | GhostLedger provenance | `provenance.py` stub | partial |
| 28 | Vultr experiment infra | planned | planned |
| 29 | Serverless inference | `model_proposals.py` stub | partial |
| 30 | Multiverse UI | `apps/web` | planned |
| 31 | Execution Director UI | `apps/web` | planned |
| 32 | Evidence knowledge UI | `apps/web` | planned |
| 33 | Benchmark scenarios | `benchmarks/m9/` | started |
| 34 | Policy benchmark | `simulator.py` + tests | done |
| 35 | Safety tests | `tests/test_safety.py` | done |
| 36 | Integration gate | `M9_FINAL.md` | planned |

Waves 0→7 per prompt §74.
