# M6 Coordination — Living Twin (30 specialists)

Lead agent **not** counted. Hard requirement: **30** workstreams.

## Contract freeze

**Wave 1:** `SourceRevisionV1`, `TwinRevisionV1`, `DriftEventV1`, `DriftSetV1`, `ImpactGraphV1`, `AssumptionV1`, `EvidenceContextV1`, `TwinStalenessV1`  
**Wave 3:** `RevalidationPlanV1`, `IncrementalCompilationPlanV1`, `SyncPolicyV1`

| agent_id | mission | owned_paths | status |
|----------|---------|-------------|--------|
| 01 | M6 audit | `docs/milestones/M6_AUDIT.md` | done |
| 02 | Research | `docs/research/M6_LIVING_TWIN_SYNTHESIS.md` | done |
| 03 | Source revision | `living_twin_m6.py` (SourceRevision) | done |
| 04 | Twin revision | `living_twin_m6.py` (TwinRevision) | done |
| 05 | Graph diff | `range-compiler/.../drift/graph_diff.py` | done |
| 06 | Stable identity | `range-compiler/.../drift/stable_id.py` | started |
| 07 | Drift classification | `drift/classify.py` | done |
| 08 | Impact architect | `ImpactGraphV1`, rules schema | done |
| 09 | Impact propagation | `drift/impact.py` | done |
| 10 | Investigation relevance | `drift/relevance.py` | done |
| 11 | Assumption graph | `AssumptionV1`, `ClaimDependencyV1` | done |
| 12 | Claim validity | `ClaimValidityV1` | done |
| 13 | Evidence context | `EvidenceContextV1` | done |
| 14 | Revalidation planner | `drift/revalidation.py` | started |
| 15 | Incremental compile | `IncrementalCompilationPlanV1` | done |
| 16 | Cache invalidation | `range-compiler` cache keys | planned |
| 17 | Full rebuild escalation | `drift/escalation.py` | started |
| 18 | Sync policy | `SyncPolicyV1`, `config/living-twin-policy.yaml` | done |
| 19 | Staleness model | `TwinStalenessV1` | done |
| 20 | Scheduler revalidation | `scheduler` compile workload hooks | planned |
| 21 | Source watch | `living-twin/watch.py` | planned |
| 22 | Terraform drift | reuse importers + diff | planned |
| 23 | K8s/Compose drift | `drift/revision_compare.py` | started |
| 24 | Multiverse UI | SourceGhost drift visuals | planned |
| 25 | Execution UI | revalidation DAG | planned |
| 26 | Evidence UI | staleness/supersession | planned |
| 27 | Benchmarks | `artifacts/benchmarks/m6/` | planned |
| 28 | Mutation corpus | `tests/fixtures/drift/` | started |
| 29 | Security/privacy | drift security tests | planned |
| 30 | Integration gate | `M6_FINAL.md`, benchmark report | planned |

## Waves

0: 01–02 | 1: 03–04,07–08,11,13,19 | 2: 05–06,09–10,12 | 3: 14–18,20 | 4: 21–23 | 5: 24–26 | 6: 27–29 | 7: 30

## Do-not-touch

Three primary UI tabs; React #185 selector patterns; production systems.
