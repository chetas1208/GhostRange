# GhostShield bypass analysis (Wave 0 → closed 2026-09-27)

Protected effects target path:

`Proposer → GhostShield → Permit → GhostExecutionGateway → Provider`

## Vultr compute call sites (audit 2026-09-27, re-verified same day)

| Path | Class | Notes |
|------|-------|-------|
| `apps/api/ghostrange_api/compute_provider.py` | **CLOSED** | `build_compute_provider()` wraps `VultrComputeProvider`/`MockComputeProvider` in `ShieldedComputeProvider` for every `GHOSTSHIELD_MODE` except `DISABLED`; `create_worker`/`terminate_worker` go through `GhostExecutionGateway.authorize` + `execute_protected`. Pre-existing (`shielded_compute.py`); re-verified, not new. |
| `apps/api/ghostrange_api/orchestrator.py` | **CLOSED** | `M2OneWorldOrchestrator._build_provider` used to return a raw `VultrAdaptedComputeProvider` (live or mock) with **no** gateway mediation at all — reachable via the live `POST /v1/m2/runs`-style route. Now routed through the new `_shield_provider()` → `ShieldedVultrAdapter` (`apps/api/ghostrange_api/shielded_vultr_adapter.py`), gating `start_provisioning`/`start_destroy` via `CREATE_WORLD`/`DESTROY_WORLD` canonical actions. `settings` (and therefore `GHOSTSHIELD_MODE`) is now a required constructor argument — there is no code path that constructs this orchestrator without an explicit shielding decision. |
| `packages/range-runtime/vultr_adapter.py` | **MEDIATED (not itself modified)** | `VultrAdaptedComputeProvider` still calls the Vultr control client directly — by design, this package is the mediated *effect*, one layer below the gate. It is safe because its only caller (`orchestrator.py`) now never invokes it directly; the gate sits at the caller boundary (see `shielded_vultr_adapter.py`), consistent with how `compute_provider.py`'s `VultrComputeProvider` is gated at its own caller boundary rather than internally. |
| `apps/api/ghostrange_api/scheduler_routes.py` (`compute_dry_check`) | **BYPASSABLE (accepted, read-only)** | Direct `RealVultrProvider(...).list_computes()` — read-only auth/listing check, no `create_compute`/`destroy_compute`/`create_world`/`destroy_world`. Left un-gated intentionally: nothing here can create or destroy billable infrastructure, so it is outside the "agents must never touch infrastructure outside their authorized scope" boundary this remediation targets. Flagged for a future SHADOW-mode audit-trail pass if full observability is wanted, but not a safety gap. |
| `packages/vultr-control/*` | TCB transport | Low-level client; callers must be gated (now true for both known API callers). |

## Policy engine change alongside this fix

`packages/ghostshield/ghostrange_ghostshield/policy_engine.py`: the P1 ownership
check (`P1_UNOWNED_RESOURCE`) previously covered `TERMINATE_WORKER` only. It now
also covers `DESTROY_WORLD`, since `ShieldedVultrAdapter.start_destroy` routes
through the same hard invariant — "never terminate/destroy an unowned Vultr
resource" applies to both worker and world destruction.

## M17 remediation — status

1. ~~Route `VultrComputeProvider.create_worker` / `terminate_worker` through `GhostExecutionGateway` when `GHOSTSHIELD_MODE=ENFORCE`.~~ **Done** (pre-existing, re-verified 2026-09-27).
2. Static test: fail CI if `create_compute` imported outside allowlist modules. **Done** — `apps/api/tests/test_ghostshield_bypass_audit.py::test_no_new_real_vultr_imports_in_api` (passing).
3. Workers: no `VULTR_API_KEY` in cloud-init (already design intent). Unchanged.
4. **New, closed 2026-09-27:** route `orchestrator.py`'s live/mock `VultrAdaptedComputeProvider` path through the same gateway pattern via `ShieldedVultrAdapter`, fail-closed (DENY/LOCKDOWN/STATE_STALE/permit issues raise `GatewayError`; the real Vultr effect callable is never invoked on any non-ALLOW verdict, and there is no except-and-fallback anywhere in the wrapper).

### Verification (2026-09-27)

Ran for real, not eyeballed:

- `apps/api/tests/test_ghostshield_bypass_audit.py` — 1 passed (static import allowlist).
- `apps/api/tests/test_ghostshield_enforce.py` — 2 passed (`compute_provider.py` ENFORCE path).
- `apps/api/tests/test_ghostshield_vultr_adapter.py` (new) — 5 passed: LOCKDOWN blocks the real `start_provisioning` call (inner never invoked); ENFORCE-ALLOW reaches the inner adapter and tracks per-(range,world) ownership; ENFORCE denies `start_destroy` on an unowned world (P1, inner never invoked); `M2OneWorldOrchestrator._build_provider` returns a `ShieldedVultrAdapter` for both live and mock inner providers under `ENFORCE`, and only returns the raw, unshielded adapter when `GHOSTSHIELD_MODE=DISABLED` (explicit operator opt-out, not a default).
- `packages/ghostshield/tests/` — all passed (policy engine, including the extended P1 check).
- Full `apps/api/tests/` (23 passed, 1 skipped) and `packages/range-runtime` + `packages/ghostgate` + `packages/contracts` (252 passed) — no regressions from this change.

## Break-glass

No `DISABLE_SAFETY=true`. Future break-glass: explicit operator record + expiry (Agent 16). `GHOSTSHIELD_MODE=DISABLED` remains the only way to get an unshielded provider on either path, and it is an explicit env var, not a silent default (`Settings.from_env()` defaults to `SHADOW`).
