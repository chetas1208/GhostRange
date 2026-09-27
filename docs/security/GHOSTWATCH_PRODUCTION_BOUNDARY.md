# GhostWatch production boundary

## Never

- Arbitrary kubectl / Terraform apply / SSH
- Model, GhostDirector, or GhostScheduler escalation of authority
- Treat missing telemetry as PASS
- Production experimentation from surprises

## May (policy-bound)

- Observe deployment revision, stage, metrics
- Deterministic invariant evaluation
- Recommend HOLD / ADVANCE / ROLLBACK
- Invoke rollback **only** when `PREAUTHORIZED_ROLLBACK` + exact `rollback_target_digest` from bundle

## Language

> GhostWatch observed the approved deployment and evaluated configured runtime invariants during the recorded window.

Not: “deployment is safe.”
