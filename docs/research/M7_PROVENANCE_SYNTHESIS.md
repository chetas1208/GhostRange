# M7 Provenance Research Synthesis

## SLSA Provenance

- **URL:** https://slsa.dev/spec/v1.1/provenance  
- **Problem:** Software artifacts need traceable build inputs/outputs.  
- **GhostRange:** Borrow **input→execution→output** chain for experiments; do **not** claim SLSA compliance without meeting requirements.  
- **Adopted:** Manifest lists materials + builder + invocation.  
- **Rejected:** Equating experiment verification with SLSA build levels.

## in-toto Attestation Framework

- **URL:** https://github.com/in-toto/attestation  
- **Model:** Envelope → Statement (subject + predicateType + predicate).  
- **GhostRange:** `GhostRangeExperimentPredicateV1` inside statement; subjects = experiment root digest.  
- **Rejected:** Custom incompatible envelope.

## DSSE (Dead Simple Signing Envelope)

- **Problem:** Sign arbitrary payloads with clear typing.  
- **GhostRange:** Compatible JSON envelope for M7 local signing; optional Sigstore later.  
- **Claim we must not make:** DSSE alone proves semantic security.

## Sigstore / Cosign

- **Problem:** Keyless OIDC-bound signing.  
- **GhostRange:** Optional `IDENTITY_BOUND_SIGNING`; default `LOCAL_DEVELOPMENT_SIGNING`.  
- **Never send:** Raw logs, prompts with secrets, full bundles to public log.

## Rekor transparency log

- **Problem:** Append-only witness for signed entries.  
- **Limitation:** Proves **existence/timeline of signed metadata**, not that remediation is secure.  
- **Modes:** OFF | LOCAL | PUBLIC_DIGEST_ONLY.

## RFC 8785 (JCS)

- **Problem:** Deterministic JSON for hashing.  
- **GhostRange:** Canonical serialization before SHA-256 roots.

## W3C PROV / RO-Crate

- **Relevance:** Graph provenance vocabulary — aligns with `ProvenanceGraphV1` node/edge types.  
- **Rejected:** Full RO-Crate export as M7 gate (optional later).

## GhostRange trust statement

Cryptography verifies **integrity and provenance linkage**. Security conclusions remain from **tests, evidence, fidelity, assumptions** — not signatures alone.
