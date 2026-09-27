# M18 GhostEvolve — coordination (54 specialists)

| agent_id | mission | owned_paths | status | promotion_status |
|----------|---------|-------------|--------|------------------|
| 01 | M18 audit | `M18_AUDIT.md` | DONE | N/A |
| 02 | Self-improvement research | `M18_SELF_IMPROVEMENT_SYNTHESIS.md` | DONE | N/A |
| 03 | Continual learning | synthesis | DONE | N/A |
| 04 | Safe policy improvement | synthesis | DONE | N/A |
| 05 | Experience contracts | `ghostevolve_m18.py` | DONE | N/A |
| 06 | Ingestion pipeline | — | TODO | blocked |
| 07 | Eligibility | `eligibility.py` | DONE | N/A |
| 08 | Experience store | `experience_store.py` | PARTIAL | N/A |
| 09 | Features | `runtime_estimator.feature_revision` | PARTIAL | N/A |
| 10 | Applicability | contract only | TODO | N/A |
| 11 | Opportunity mining | `planner.py` | PARTIAL | N/A |
| 12 | Self-assessment | contract + planner | PARTIAL | N/A |
| 13 | Attribution | `planner.py` | PARTIAL | N/A |
| 14 | Evolution planner | `planner.py` | PARTIAL | N/A |
| 15 | Candidate contracts | `EvolutionCandidateV1` | DONE | N/A |
| 16 | Version registry | `candidate_registry.py` | PARTIAL | offline |
| 17 | Reproducible training | manifest digests | PARTIAL | N/A |
| 18 | Runtime estimator learner | `runtime_estimator.py` | DONE | offline |
| 19 | Startup estimator | — | TODO | N/A |
| 20 | Cost model | — | TODO | N/A |
| 21 | CPU/GPU crossover | — | TODO | N/A |
| 22 | Straggler model | — | TODO | N/A |
| 23 | Speculation policy | — | TODO | offline |
| 24 | Warm retention | regression test only | PARTIAL | rejected demo |
| 25 | Stopping policy | — | TODO | N/A |
| 26 | Director ranking | offline-only | TODO | N/A |
| 27 | Memory selection | — | TODO | N/A |
| 28 | Retrieval drift | — | TODO | N/A |
| 29 | Replay engine | `replay_engine.py` | PARTIAL | N/A |
| 30 | Off-policy eval | `OFF_POLICY_UNKNOWN` | PARTIAL | N/A |
| 31 | Simulation eval | scheduler sim | TODO | N/A |
| 32 | Temporal split | `evaluation.py` | DONE | N/A |
| 33 | Holdout | tests | PARTIAL | N/A |
| 34 | Regression | `evaluation.py` | PARTIAL | N/A |
| 35 | Forgetting | `forgetting_report` | PARTIAL | N/A |
| 36 | Drift detection | contract only | TODO | N/A |
| 37 | Provider drift | — | TODO | N/A |
| 38 | Shadow mode | UI + contract | PARTIAL | no live |
| 39 | Canary | — | TODO | blocked |
| 40 | Promotion | `promotion.py` | PARTIAL | shield |
| 41 | GhostShield bridge | `PROMOTE_EVOLUTION_CANDIDATE` | DONE | required |
| 42 | Rollback | `EvolutionRollbackV1` + registry | PARTIAL | N/A |
| 43 | Evolution budget | contract | CONTRACT | N/A |
| 44 | Value/amortization | contract | CONTRACT | N/A |
| 45 | Ledger provenance | — | TODO | N/A |
| 46 | Multiverse UI | `EvolutionMarker` | PARTIAL | N/A |
| 47 | Execution UI | Champion/Challenger/Shadow | PARTIAL | N/A |
| 48 | Evidence UI | — | TODO | N/A |
| 49 | Poisoning red team | unit test | DONE | N/A |
| 50 | Regression red team | unit test | PARTIAL | N/A |
| 51 | Promotion bypass red team | promotion tests | DONE | N/A |
| 52 | Drift/forgetting red team | regression test | PARTIAL | N/A |
| 53 | Research integrity | synthesis | DONE | N/A |
| 54 | Final reviewer | `M18_FINAL.md` | **NO-GO** | no auto promote |

**Blockers:** M17 GO, Postgres store, live shadow/canary, sufficient real worker history.
