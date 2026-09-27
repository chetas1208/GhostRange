# Shadow, canary, promotion

**Shadow:** challenger receives same inputs as champion; records decisions/predictions; **no effectful control**.

**Canary:** small deterministic fraction of eligible decisions (runtime estimator first); GhostShield unchanged.

**Promotion:** `EvolutionPromotionRequestV1` + human `approval_digest` + `EvolutionPromotionGate` → `PROMOTE_EVOLUTION_CANDIDATE`.

Candidate digest swap → hard fail.
