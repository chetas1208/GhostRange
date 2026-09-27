# M14 Audit — M13 inheritance

## M13 reality (not assumed complete)

| Capability | Classification |
|------------|----------------|
| 5-node GhostMeshHarness | REAL_VERIFIED (simulated) |
| Live Vultr federation | LIVE_MESH_NOT_RUN |
| Agent 40 M13 GO | INHERITED_BLOCKER — NO-GO |
| Structural applicability | REAL_PARTIAL |
| Full semantic privacy / 12 screenshots | INHERITED_BLOCKER |

M14 uses **GhostCausalSimulator** + existing Mesh harness for transport demos — labeled **SIMULATED_SCM**.

## Ready for M14

- MeshPrior / applicability baseline for comparison
- GhostDirector experiment proposal pattern
- Disposable-world intervention semantics (range-bound)
- Three-tab UI constraint

## M14 starting point

| Component | Classification |
|-----------|----------------|
| ghostcausal_m14 contracts | REAL_VERIFIED |
| CausalInvestigationEngine | REAL_PARTIAL |
| Transportability B/C | REAL_VERIFIED (sim) |
| DoWhy/EconML integration | NOT STARTED |
| LIVE_CAUSAL_CAMPAIGN | NOT RUN |

Tests: `pytest packages/ghostcausal/tests`
