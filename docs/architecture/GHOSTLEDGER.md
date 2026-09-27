# GhostLedger (M7)

GhostLedger makes GhostRange experiment **integrity and provenance** independently verifiable without trusting the application database.

## What cryptography covers

- Canonical JSON digests (RFC 8785–inspired sorted keys) for manifest, provenance graph, experiment root
- SHA-256 content addressing for evidence artifacts
- Merkle root over artifact digests in the experiment root
- Hash-chained domain events (tamper-evident sequencing, not deletion-proof without external anchor)
- Ed25519 signatures over an in-toto Statement–shaped payload with `GhostRangeExperimentPredicateV1`

## What cryptography does **not** cover

- Semantic correctness of remediation or verification conclusions
- Model nondeterminism or cloud timing
- Trust in signer identity unless `TrustPolicyV1` is configured

## Packages

| Package | Role |
|---------|------|
| `packages/contracts/ghostledger_m7.py` | Schemas: manifest, graph, root, attestation, bundle |
| `packages/ghostledger/` | Seal, verify, CAS store, CLI `ghostrange-verify verify <bundle.json>` |

## Offline verification

```bash
pip install -e packages/contracts -e packages/ghostledger
ghostrange-verify verify tests/fixtures/bundles/valid-full.json
```

Bundle JSON may wrap `{ "bundle": {...}, "trusted_public_keys": { "ghostrange-dev": "-----BEGIN PUBLIC KEY-----..." } }`.

## Development signing

`LOCAL_DEVELOPMENT` Ed25519 keys (`DevSigner`) are ephemeral and must not be presented as production trust.

## Future (not required for first gate)

- Sigstore / Rekor (`PUBLIC_DIGEST_ONLY` mode)
- Live Vultr replay orchestration
- Evidence UI provenance constellation wiring
