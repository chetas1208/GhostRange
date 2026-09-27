# Action authorization boundary

Protected today (partial):

- `CREATE_WORKER` / `TERMINATE_WORKER` via `ShieldedComputeProvider`

Still bypassable:

- `apps/api/ghostrange_api/orchestrator.py` (golden path)
- `packages/range-runtime/.../vultr_adapter.py` (world/compute for ranges)

Permit binds: action digest, principal, policy version, state revision, campaign id, expiry, single-use consumption at gateway.

Mutation: execution compares `permit.action_digest` to `action.canonical_digest()` before effect.
