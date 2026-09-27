# M10 Capability Matrix

Binary columns: **Y** / **N** / **—** (not applicable). Notes where non-obvious.

| Capability | contract | impl | unit | integration | mock E2E | live E2E | UI | provenance | failure tested | release ready |
|------------|----------|------|------|-------------|----------|----------|-----|------------|----------------|---------------|
| Range Compiler | Y | Y | Y | N | N | N | N | N | N | N |
| Fidelity Engine | Y | Y | Y | N | N | N | N | N | N | N |
| Vultr provisioning | Y | Y | partial | N | Y | N | partial | N | N | N |
| World lifecycle | Y | Y | Y | Y | Y | N | Y fixture | N | N | N |
| World forking | Y | partial | N | N | N | N | fixture | N | N | N |
| GhostScheduler | Y | Y | Y | N | Y | N | fixture | N | N | N |
| GhostDirector | Y | Y | Y | N | N | N | N | N | N | N |
| Evidence | Y | Y | Y | Y | Y | N | fixture | partial | N | N |
| GhostLedger | Y | Y | Y | N | N | N | N | N | N | N |
| Living Twin | Y | Y | Y | N | N | N | N | N | N | N |
| Adversarial Verification | Y | Y | Y | N | N | N | N | N | N | N |
| Replay | Y | partial | N | N | N | N | N | N | N | N |
| Serverless Inference | — | N | — | N | N | N | N | N | N | N |
| 3D Multiverse | — | Y | Y | N | fixture | N | Y | — | N | N |
| 3D Execution | — | Y | Y | N | fixture | N | Y | — | N | N |
| 3D Evidence | — | Y | Y | N | fixture | N | Y | — | N | N |
| SSE / live events | Y | Y | Y | Y | Y | N | partial | N | N | N |
| Cost accounting | partial | partial | N | N | partial | N | fake in fixture | N | N | N |
| Teardown | Y | Y | partial | Y | Y | N | partial | N | N | N |
| Orphan reconciliation | Y | partial | N | N | N | N | N | N | N | N |
| **M10 golden path (unified)** | — | **started** | **started** | **started** | **target** | **blocked** | **target** | **target** | N | N |

**Live E2E column:** requires `GHOSTRANGE_LIVE=true` + credentials + resource lease (M10).
