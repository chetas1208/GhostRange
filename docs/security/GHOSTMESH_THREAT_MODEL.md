# GhostMesh Threat Model

See `GhostMeshThreatModelV1` in contracts.

## In scope adversaries

- Honest-but-curious coordinator (sees contribution digests/metadata)
- Malicious participant (poisoned or smuggled execution strings)
- Sybil identities (membership policy + rate limits — partial in M13)
- Membership / reconstruction attackers on aggregates

## Out of scope (M13 v1)

Physical access, side channels, compromised TLS roots on live deploy.

## Fail-safe behaviors

- DLP failure → do not publish
- Quarantine → not distributed as active prior
- Local policy may reject federation-accepted contributions
- No remote execution messages in protocol

## Automatic NO-GO conditions (Agent 40)

Raw tenant evidence crosses Mesh; remote contribution creates local verified claim; Mesh grants production control.
