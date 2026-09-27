# M13 GhostMesh — Research Synthesis

## Hard principle

**Federation is not a privacy guarantee.** NIST PPFL guidance stresses explicit threat models, poisoning, secure aggregation where applicable, and the gap between algorithmic assumptions and deployment. Model updates and aggregates can leak training information.

GhostMesh v1 prioritizes **federated knowledge artifacts** (inspectable, revocable) over a global neural model.

## Sources (selected)

| Title | Problem | GhostRange relevance | Adopt | Reject |
|-------|---------|------------------------|-------|--------|
| NIST PPFL (draft guidance) | PPFL threat models, poisoning, heterogeneity | Mandatory threat model doc | Explicit attacker classes, no “private by default” claims | Blind FL deployment |
| Argo Rollouts / Flagger (M12 prior) | Progressive delivery observation | Separate from Mesh; no prod telemetry share | Rollback *patterns* abstracted only | Raw metrics federation |
| Federated digital twins (2026 literature) | Collaboration + inference/poisoning | Inspiration for cross-silo learning | Local twin validation loop | Central twin DB |
| OpenFeature | Vendor-neutral flags | Optional rollout class metadata | Abstract flag-state patterns | Remote flag admin |

## GhostMesh design choices

1. **KnowledgeClassV1** structured contributions, not gradient dumps (v1 default).
2. **KnowledgePrivacyTransformV1** pipeline: classify → remove IDs → generalize → DLP → optional DP on aggregates only.
3. **Local validation** before any claim linkage; remote status never `CURRENT` on ClaimV1.
4. **Poisoning**: schema + DLP + quarantine; strongest defense remains local re-test.
5. **Exploration reserve** in Director bridge to mitigate defense monoculture.

## What we must not claim

- “No data leaves the customer” — transformed knowledge may leave when sharing is authorized.
- “Anonymous federation” — use pseudonymous node identity where configured.
- “Remote knowledge verified” — only locally validated with local evidence.

## Negative results to report

Measure when **NO_SHARING** or **STATIC_ABSTRACT_PATTERN** beats GhostMesh on utility, and when Mesh priors cause **NegativeTransferV1** (tenant C benchmark).
