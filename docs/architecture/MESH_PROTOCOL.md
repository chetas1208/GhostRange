# GhostMeshProtocolV1

Versioned envelopes (`GhostMeshProtocolEnvelopeV1`):

| Kind | Purpose |
|------|---------|
| CONTRIBUTION | Structured knowledge artifact digest |
| AGGREGATE | Cohort statistics |
| REVOCATION | ContributionRevocationV1 |
| SCHEMA | Contract version advertisement |
| RECEIPT | MeshReceiptV1 |
| MEMBERSHIP | Federation roster update |
| HEARTBEAT | Liveness |

**Forbidden:** arbitrary RPC, execution, deploy, rollback, attack commands.

Authentication: mTLS/OIDC in production; simulated harness uses pseudonym node IDs.
