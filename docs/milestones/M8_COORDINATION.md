# M8 Coordination — Adversarial Verification Engine (34 specialists)

Lead owns architecture, contract freezes, integration, safety review, release gate.

## Contract freeze

**Wave 1:** `FalsificationConditionV1`, `CounterexampleV1`, `AdversarialSearchPlanV1`, `AdversarialBudgetV1`, `MutationOperatorV1`, `SecurityOracleV1`  
**Wave 3:** `SearchArmV1`, `SearchMemoryV1`, `ObservationNoveltyV1`, `SearchTreeV1`  
**Wave 4:** `AssumptionChallengeV1`, `RemediationRevisionV1`, `VerificationSuiteRevisionV1`, `AdversarialVerificationReportV1`

| agent_id | mission | owned_paths | status |
|----------|---------|-------------|--------|
| 01 | M8 audit | `M8_AUDIT.md` | done |
| 02 | Adversarial research | `M8_ADVERSARIAL_VERIFICATION_SYNTHESIS.md` | done |
| 03 | Falsification architect | `adversarial_m8.py` (FalsificationCondition) | done |
| 04 | Counterexample contracts | `adversarial_m8.py` (Counterexample) | done |
| 05 | Search plan | `adversarial_m8.py` (AdversarialSearchPlan) | done |
| 06 | Search space | `search_space.py` | done |
| 07 | Mutations | `mutations.py` | done |
| 08 | Search safety | `safety.py` | done |
| 09 | Security oracle | `oracle.py` | done |
| 10 | Differential worlds | `differential.py` | done |
| 11 | Property-based | `hypothesis_gen.py` (optional stub) | partial |
| 12 | Metamorphic | `metamorphic.py` | partial |
| 13 | Sequence search | `mutations.py` (sequence) | done |
| 14 | Identity state | `mutations.py` (identity) | done |
| 15 | Timing/concurrency | `mutations.py` (timing stub) | partial |
| 16 | Dependency variation | `scenarios/*` stubs | partial |
| 17 | Search memory | `search_memory.py` | done |
| 18 | Novelty | `novelty.py` | done |
| 19 | Search baselines | `policies.py` | done |
| 20 | GhostScheduler search | `search_scheduler.py` | done |
| 21 | Bandit research | `docs/research/` notes only | planned |
| 22 | Minimization | `minimize.py` | done |
| 23 | Confirmation | `confirm.py` | done |
| 24 | Assumption challenge | `assumption_challenge.py` | done |
| 25 | Remediation revision | `remediation_revision.py` | done |
| 26 | Suite evolution | `suite_evolution.py` | done |
| 27 | GhostLedger provenance | `provenance_hooks.py` | partial |
| 28 | Vultr search infra | `infra/` stub | planned |
| 29 | Serverless hypothesis | `hypothesis_llm.py` stub | planned |
| 30 | Multiverse UI | `apps/web` | planned |
| 31 | Execution UI search tree | `apps/web` | planned |
| 32 | Evidence UI counterexample | `apps/web` | planned |
| 33 | Benchmark corpus | `benchmarks/m8/` | started |
| 34 | Integration / safety gate | `M8_FINAL.md` | planned |

Waves: 0→1→2→3→4→5→6→7 per prompt §72.
