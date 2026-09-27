# Experience model

`ExperienceRecordV1` — immutable raw digest + eligibility label.

Eligibility pipeline: provenance → safety → quality → `LearningEligibility`.

Near-miss (`AUTHORIZATION_DENIAL`) → `ELIGIBLE_WITH_LIMITATIONS`.

Poison/fixture → `QUARANTINED` / `REJECTED`.

Store v1: `GhostExperienceStore` (memory/file). Target: Postgres metadata + Object Storage traces.
