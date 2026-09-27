# M7 Final — GhostLedger (in progress)

**Status:** Core integrity path implemented; full completion gate (§125) **not** met.

## What is an experiment?

- **Definition:** stable slug (`ExperimentDefinitionV1.definition_id`, e.g. `auth-remediation-v1`)
- **Run:** unique `run_id` (`ExperimentIDV1`) — one sealed execution instance

## ExperimentManifestV1

Captures source/twin revision hashes, compiler and scheduler policy refs, model/tool/infra records (schemas in `ghostledger_m7.py`), investigation objective, initiator, budget — **no secrets**.

## Experiment root

`ExperimentRootV1` = canonical digest of:

1. manifest  
2. provenance graph (content digest excluding embedded `graph_digest` field)  
3. artifact Merkle root  
4. event log root (last chained event hash)  
5. claim set digest  

Then `root_digest` = SHA-256 of those five fields (canonical JSON).

## Cryptographically covered

Manifest/graph/root consistency, artifact Merkle root, hash-chained events, Ed25519 signature over in-toto Statement + `GhostRangeExperimentPredicateV1`.

## Not covered

Semantic security conclusions, LLM nondeterminism, deletion of events without external anchor, trust in unknown signers.

## Signing model

`LOCAL_DEVELOPMENT` — Ed25519 via `cryptography` (`DevSigner`). Production identity-bound / Sigstore: **planned**, not integrated.

## Root of trust (offline verifier)

- GhostRange v1 schemas  
- SHA-256 + canonical JSON  
- Configured trusted public keys (`key_id` → PEM)

## in-toto / Sigstore / Rekor

- **in-toto:** Statement-shaped signing payload; predicate type `https://ghostrange.local/attestation/experiment/v1`  
- **Sigstore / Rekor:** not wired; transparency modes documented in contracts only

## Offline verification

`ghostrange-verify verify <bundle.json>` — 8 unit tests pass; golden `valid-full.json`, `tampered-manifest.json`.

## Replay / UI / live Vultr

**Not implemented** in this milestone slice (`ReplayPlanV1` contracts only).

## Storage overhead

Not benchmarked yet (`artifacts/benchmarks/m7/` empty).

## Ready for M8

Integrity-first audit bundles and offline verify — **foundation ready**. Adversarial counterexample search remains M8.

## Completion gate checklist

See prompt §125 — majority items remain open (API export, redaction pipeline, full tamper matrix, replay, UI, E2E demo, benchmarks).
