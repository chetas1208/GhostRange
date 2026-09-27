# GhostMesh Architecture (M13)

```
Organization A (GhostRange)          Organization B
        |                                    |
   Local GhostLedger                   Local GhostLedger
        |                                    |
   KnowledgeExtractor                  KnowledgeApplicabilityEngine
        |                                    ^
   Privacy Transform                          |
        |                              MeshPrior → Director
        v                                    |
   Signed MeshContribution  ──protocol──►  Receive + Receipt
        |                                    |
   Coordinator (aggregates digests)     Local experiment (Vultr world)
```

## Rules

1. Default `sharing_enabled: false` (`config/mesh-contribution-policy.yaml`).
2. Remote knowledge **never** auto-updates local claims.
3. Protocol message kinds are fixed (`GhostMeshProtocolV1`); no arbitrary RPC.
4. Mesh outage must not block GhostDirector, GhostScheduler, GhostWatch, or GhostGate locally.

## Code map

- Contracts: `packages/contracts/ghostrange_contracts/ghostmesh_m13.py`
- Engine: `packages/ghostmesh/ghostrange_ghostmesh/`
- Harness: `GhostMeshHarness` (tenants A–E)
- API: `apps/api/ghostrange_api/mesh_routes.py`
