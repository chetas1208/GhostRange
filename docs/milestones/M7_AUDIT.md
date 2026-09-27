# M7 Audit — Wave 0 (2026-09-26)

Verified state before GhostLedger work.

## Tests (run separately — `test_scheduler` name collision)

| Suite | Result |
|-------|--------|
| `pytest packages/contracts` | 78 pass (after M7 contract tests) |
| `pytest packages/range-compiler` | 9 pass |
| `pytest packages/scheduler` | 119 pass |
| `pytest packages/evidence` | pass (prior) |

## M6 reality

| Item | Status |
|------|--------|
| Living twin drift engine | **IMPLEMENTED** (unit tests) |
| Claim validity STALE/CURRENT | **PARTIAL** (contracts + planner, not persisted in API) |
| Source/twin revisions | **CONTRACT + in-memory** |
| M6 API/events/UI | **NOT DONE** |

## M7 readiness

| Existing asset | M7 use |
|----------------|--------|
| `ArtifactV1.content_hash` + object store | Content addressing — extend for bundles |
| `ProvenanceStore` | Metadata graph seed |
| `living_twin_m6` revisions | Manifest inputs |
| `RangeCompiler` manifests | Compiler provenance fields |
| Scheduler V3 `PlanActionV1` | Scheduler provenance |

## BLOCKING_M7 (before gate)

- End-to-end experiment capture from live API run  
- Sigstore/Rekor production integration (optional path)  
- Full in-toto library conformance (start with compatible envelope)  
- Event hash chain in production event gateway  
- Live Vultr replay from bundle  

## Security notes

- No blockchain  
- No custom crypto — Ed25519 via `cryptography` for local dev signing  
- Bundles are **untrusted input** on import  
