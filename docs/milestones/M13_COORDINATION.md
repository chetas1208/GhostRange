# M13 GhostMesh — 40 Specialist Agents

Lead agent (not counted): architecture, contract arbitration, integration, Agent 40 gate.

| agent_id | mission | owned_paths | dependencies | status | deliverables | tests | reviewer | integration | privacy_review | security_review |
|----------|---------|-------------|--------------|--------|--------------|-------|----------|-------------|----------------|-----------------|
| 01 | M12/M13 audit | docs/milestones/M13_AUDIT.md | M12_FINAL | DONE | audit classifications | manual | 40 | merged | pass | pass |
| 02 | PPFL research | docs/research/M13_GHOSTMESH_SYNTHESIS.md | — | DONE | synthesis table | — | 40 | merged | pass | — |
| 03 | Threat model | docs/security/GHOSTMESH_THREAT_MODEL.md, GHOSTMESH_PRIVACY_MODEL.md | 02 | DONE | GhostMeshThreatModelV1 | — | 40 | merged | pass | pass |
| 04 | Knowledge taxonomy | ghostmesh_m13.py KnowledgeClass | — | DONE | 10 classes | contract | lead | frozen W1 | — | — |
| 05 | Contribution contracts | MeshContributionV1, privacy profile | 04 | DONE | shareable artifact | contract | lead | frozen W1 | pass | pass |
| 06 | Extraction | extract.py | 04 | DONE | candidate knowledge | test_ghostmesh | 30 | yes | local-only | — |
| 07 | Abstraction | abstraction.py | 06 | DONE | KnowledgeAbstractionV1 | test_privacy_redteam | 08 | yes | pass | — |
| 08 | DLP | dlp.py | 05 | DONE | ContributionDLP | test_privacy_redteam | 36 | yes | pass | pass |
| 09 | Semantic privacy | semantic_privacy.py | 08 | DONE | leakage report | test_privacy_redteam | 36 | yes | pass | — |
| 10 | Differential privacy | differential_privacy.py | 02 | DONE | PrivacyBudgetV1 laplace | benchmark_m13 | 03 | partial | pass | — |
| 11 | Secure aggregation | secure_aggregation.py | 02 | DONE | pedagogical secure sum | — | 03 | research | — | — |
| 12 | Federation identity | MeshNodeIdentityV1, sybil.py | — | DONE | membership + quota | test_poisoning_redteam | 19 | yes | — | pass |
| 13 | Mesh protocol | protocol.py, MESH_PROTOCOL.md | 05 | DONE | envelope v1 | test_waves | lead | frozen W2 | — | pass |
| 14 | Knowledge registry | registry.py | 05 | DONE | MeshKnowledgeRegistry | test_waves | 16 | yes | pass | — |
| 15 | Deduplication | deduplication.py | 14 | DONE | KnowledgeFingerprintV1 | coordinator | 16 | yes | — | — |
| 16 | Aggregation | registry aggregate + federated_analytics.py | 10,14 | DONE | AggregatedKnowledgeV1 | API cohort | 27 | yes | pass | — |
| 17 | Trust/quality | quality.py | 05 | DONE | ContributionQualityV1 | — | 18 | yes | — | — |
| 18 | Poisoning defense | poisoning.py | 08 | DONE | quarantine | test_poisoning_redteam | 37 | yes | — | pass |
| 19 | Sybil security | sybil.py, coordinator | 12 | DONE | quotas | test_poisoning_redteam | 37 | yes | — | pass |
| 20 | Revocation | revocation.py | 14 | DONE | propagate revoke | test_waves | 40 | yes | — | pass |
| 21 | Unlearning research | docs/research/M13_UNLEARNING.md | 20 | DONE | honest limits doc | — | 40 | doc | — | — |
| 22 | Applicability | applicability.py | 07 | DONE | ApplicabilityReportV1 | test_ghostmesh | 23 | yes | — | — |
| 23 | Director mesh | director_bridge.py | 22 | DONE | MeshPrior ordering | test_ghostmesh | 40 | yes | — | — |
| 24 | M8 search prior | search_prior.py | 23 | DONE | search families | test_waves | 23 | yes | — | — |
| 25 | Scheduler mesh | scheduler_prior.py | 05 | DONE | SchedulerHintV1 | — | lead | advisory | pass | — |
| 26 | GhostWatch abstract | ghostwatch_abstract.py | 07 | DONE | surprise tags | — | 26 | partial | pass | — |
| 27 | Federated analytics | federated_analytics.py | 10,16 | DONE | cohort stats | API | 38 | yes | pass | — |
| 28 | Federated prior model | federated_model.py | 23 | EXPERIMENT | rank only | test_waves | 29 | yes | — | — |
| 29 | Model privacy attacks | model_privacy.py | 28 | DONE | probe benchmarks | benchmark_m13 | 40 | yes | pass | pass |
| 30 | GhostLedger mesh | ledger_bridge.py | 06 | PARTIAL | provenance log | test_waves | 40 | in-memory | pass | — |
| 31 | 5-node harness | harness.py | 13,18 | DONE | A–E story | test_ghostmesh | 38 | yes | pass | pass |
| 32 | Vultr federation | docs/infra/M13_VULTR_MESH.md | 31 | LIVE_MESH_NOT_RUN | isolation plan | — | 39 | blocked | — | pass |
| 33 | Multiverse mesh UI | ui/mesh/*.tsx MeshSignal | — | DONE | abstract signals | manual | 35 | yes | pass | — |
| 34 | Execution mesh UI | MeshExecutionHint.tsx | 23 | DONE | prior flow DOM | manual | 35 | yes | — | — |
| 35 | Evidence mesh UI | MeshPanel.tsx | 30 | DONE | provenance DOM | manual | 40 | yes | pass | — |
| 36 | Privacy red team | tests/test_privacy_redteam.py | 08,09 | DONE | attack corpus | pytest | 40 | yes | fail-closed | — |
| 37 | Poisoning red team | tests/test_poisoning_redteam.py | 18,19 | DONE | E node | pytest | 40 | yes | — | pass |
| 38 | Benchmark | scripts/benchmark_m13.py | 31 | DONE | summary.json | script | 40 | yes | measured | — |
| 39 | Operations | OPERATIONS_GHOSTMESH.md | 12 | DONE | opt-in policy | — | 40 | yes | pass | pass |
| 40 | Final reviewer | M13_FINAL.md, AGENT_40_REVIEW.md | all | **NO-GO** | GO/NO-GO | gate checklist | — | — | reviewed | reviewed |

**Waves executed:** 0–6 complete (simulated); Wave 7 Agent 40 **NO-GO** (live federation, screenshots, full semantic red team, durable GhostLedger seal).

**Production access:** none for any agent.
