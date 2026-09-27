# M7 Coordination — GhostLedger (32 specialists)

## Contract freeze

**Wave 1:** `ExperimentIDV1`, `ExperimentManifestV1`, `ProvenanceGraphV1`, `DisclosurePolicyV1`, `ReplayPlanV1`, `ReplayLevelV1`  
**Wave 3:** `ExperimentRootV1`, `ExperimentAttestationV1`, `GhostBundleV1`  
**Wave 5:** `ReplayComparisonV1`

| agent_id | mission | owned_paths | status |
|----------|---------|-------------|--------|
| 01 | M7 audit | `M7_AUDIT.md` | done |
| 02 | Provenance research | `M7_PROVENANCE_SYNTHESIS.md` | done |
| 03 | Experiment manifest | `ghostledger_m7.py` | done |
| 04 | Provenance graph | `seal.build_provenance_graph` | done |
| 05 | Canonicalization | `ghostledger/canonical.py` | done |
| 06 | Content addressing | `artifact_store.py` | done (local CAS) |
| 07 | Merkle | `ghostledger/merkle.py` | done |
| 08 | Event integrity | `ghostledger/event_chain.py` | done |
| 09 | in-toto envelope | `seal.py` Statement + predicate | done |
| 10 | Local signing | `ghostledger/signing.py` | done |
| 11 | Sigstore | `ghostledger/sigstore.py` | planned |
| 12 | Transparency log | `ghostledger/transparency.py` | planned |
| 13 | Redaction | `ghostledger/redaction.py` | started |
| 14 | Bundle | `seal.py` → `GhostBundleV1` | done (JSON bundle) |
| 15 | Offline verifier | `verify.py`, `cli.py` | done |
| 16 | Tamper tests | `tests/fixtures/bundles/` + pytest | done (subset) |
| 17 | Source/twin lineage | `manifest_builder.py` | started |
| 18 | Scheduler provenance | capture hooks | planned |
| 19 | Model provenance | `ModelInvocationRecordV1` | done |
| 20 | Tool provenance | `ToolInvocationRecordV1` | done |
| 21 | Infra provenance | `InfrastructureRecordV1` | done |
| 22 | Claim attestation | `claim_bind.py` | planned |
| 23 | Replay architect | contracts | done |
| 24 | Offline replay | `replay/offline.py` | planned |
| 25 | Live replay | `replay/live.py` | planned |
| 26 | Model replay | `replay/model.py` | planned |
| 27 | Replay comparison | `ReplayComparisonV1` | done |
| 28 | Evidence UI | web Evidence | planned |
| 29 | Multiverse replay UI | web Multiverse | planned |
| 30 | Benchmarks | `artifacts/benchmarks/m7/` | planned |
| 31 | Security review | security tests | planned |
| 32 | Integration gate | `M7_FINAL.md` | planned |

Waves: 0→1→2→3→4→5→6→7 per prompt §71.
