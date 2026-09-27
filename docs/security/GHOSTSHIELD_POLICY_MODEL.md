# GhostPolicyV1 (embedded engine)

Version: `ghostshield/v1`

Kinds supported in engine (subset): PRECONDITION, INVARIANT, BUDGET_CONSTRAINT, APPROVAL_CONSTRAINT.

Hard properties implemented:

- **P1** unowned terminate → DENY
- **P2** max active workers → DENY
- **P3** GPU without `allow_live_gpu` → DENY
- **P11** SAFE_MODE → DENY create worker/world
- Budget hard cap → DENY
- Rollback without approval digest → REQUIRE_HUMAN

Human explanation is structured from `reason_codes`, not LLM verdict.
