# Evolution pipeline

States: `PROPOSED → TRAINED → OFFLINE_EVALUATION → (REJECTED | SHADOW → CANARY → PROMOTED)`.

Gates: temporal split, holdouts, regression slices, safety, shadow disagreement analysis, human approval, GhostShield permit bound to **exact** `candidate_digest`.

Rollback: `EvolutionRollbackV1` to version preserved in champion history.

No-update and insufficient-data are **successful** outcomes.
