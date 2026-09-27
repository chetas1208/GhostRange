# M13 — Machine Unlearning (Agent 21)

GhostMesh revocation removes contributions from the **active registry** and marks `REVOKED` provenance.

**Do not claim exact unlearning** for `FederatedPriorModelV1` without retraining evidence.

Options when a federated prior model incorporated revoked knowledge:

1. **Checkpoint rollback** to pre-contribution round (if round boundaries recorded).
2. **Retrain** without revoked fingerprint (expensive, honest).
3. **Down-weight** rank key in `rank_weights` (heuristic, not cryptographic unlearning).

M13 implements (3) only as documentation — not automated unlearning.
