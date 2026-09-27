# M6 Living Twin Research Synthesis

Thesis: **security-relevant, impact-aware sync** preserves valid claims with less rebuild/reverify than full refresh, without unsafe claim preservation.

## Digital Twin Synchronization (data-centric architecture, ~2026)

- **Problem:** Physical/source vs twin state alignment over time.  
- **Method:** Data-centric sync architecture rather than ad hoc polling.  
- **GhostRange:** Event-sourced **source revisions** + semantic graph diff; no continuous byte mirror.  
- **Do not claim:** Full DT sync solved; we sync **investigation-relevant** properties only.

## Predict First, Sync When Needed (NOMS 2026, risk-aware adaptive DT)

- **Problem:** Continuous sync wastes bandwidth/compute.  
- **Method:** Predict drift risk; sync when needed.  
- **GhostRange:** `SyncPolicyV1` — IGNORE / RECORD_ONLY / INVALIDATE / INCREMENTAL / FULL.  
- **Do not claim:** Same prediction model without our benchmarks.

## Drift-adaptive synchronization (energy–fidelity tradeoffs, 2026)

- **Problem:** Fidelity vs cost of keeping twin fresh.  
- **GhostRange:** Tie to `FidelityProfileV1` — resource drift ignored when dimension IGNORED.  
- **Do not claim:** Energy metrics; we track compute/cost via GhostScheduler.

## Semantic drift in digital twin frameworks (2026)

- **Problem:** Binary “in sync” hides meaningful model changes.  
- **GhostRange:** `SemanticDriftCategory` aligned with M5 fidelity dimensions.  
- **Do not claim:** Semantic equivalence = security equivalence.

## Change impact analysis in microservices evolution (SANER 2025)

- **Problem:** Ripple effects of architecture/config changes.  
- **GhostRange:** `ImpactGraphV1` typed propagation along `DEPENDS_ON`, `AUTHENTICATES_VIA`, etc.  
- **Do not claim:** Full microservice CI/CD impact tool.

## SAFARI / Security-investigation-as-code

- **Relevance:** Reproducible twins from IaC; M6 adds **revision lineage + claim invalidation**.  
- **Do not claim:** SAFARI integration complete.

## Incremental build / dependency invalidation (build systems mental model)

- **Adopted:** Source → graph → twin → verification → claim DAG; change invalidates dependents.  
- **GhostRange addition:** Security semantics, mandatory tests, conservative UNKNOWN.

## Rejected

- Continuous production polling  
- Text-diff-as-truth  
- LLM-only impact analysis  
- Deleting stale evidence  
