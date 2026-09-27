# Deployment authority (M12)

See `packages/ghostwatch/ghostrange_ghostwatch/authority.py`.

- Default: `OBSERVE_ONLY`
- Kill switch: `GHOSTWATCH_CONTROL_DISABLED=true`
- Preauthorized rollback requires exact `rollback_target_digest` match
- Forbidden action types: `ArbitraryKubectlAction`, `ProductionShellAction`, etc.
