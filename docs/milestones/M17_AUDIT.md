# M17 Audit — Wave 0 (2026-09-27)

## M16 prerequisite checklist

| Gate | Status | Class |
|------|--------|-------|
| Canonical campaign state | PARTIAL | `campaign_runtime` schema + contracts; **no live PG store wired** |
| Side-effect intent durable | **STUB** | Journal not on Vultr create/terminate path |
| Idempotency | REAL_PARTIAL | Worker tasks + gate promotion |
| Runtime fencing | **FORMALLY_UNSPECIFIED** live |
| Checkpoints | REAL_PARTIAL | GhostLedger event digests |
| Recovery works | SIMULATED | `CampaignRecoveryManager` unit tests only |
| Provider reconciliation | **STUB** | `reconcile.py` placeholder |
| Budget survives restart | **NON_DURABLE** | Env caps only at authorize time |
| Stale workers cannot commit | REAL_PARTIAL | Worker auth tokens |
| Duplicate consequential effects contained | **NOT_COVERED** |
| Live campaigns `owned_workers == []` | REAL_PARTIAL | Mock E2E; live blocked (Vultr ACL) |

**M16 live GO:** NO-GO → M17 may build models, policy engine, simulator, shadow mode. **Non-bypassable live ENFORCE** is **not fully claimable** until worker path + range-runtime bypasses close.

## GhostShield implementation (this repo)

| Component | Class | Notes |
|-----------|-------|-------|
| `ghostshield_m17` contracts | READY_FOR_M17 | Actions, verdicts, permits, trust model |
| `GhostShieldPolicyEngine` | REAL_PARTIAL | P1, P2, P3, P11, budget, rollback approval |
| `GhostExecutionGateway` | REAL_PARTIAL | SHADOW/ENFORCE/LOCKDOWN; TOCTOU re-check |
| `ShieldedComputeProvider` | REAL_PARTIAL | Worker create/terminate only |
| `GhostRuntimeMonitor` | **STUB** | P2 pre-action only |
| TLA+ `WorkerFleet.tla` | REAL_PARTIAL | Invariant `NeverExceedMax`; **TLC not run in CI** |
| UI `ActionGate` / `ActionPermit` | REAL_PARTIAL | Execution tab only; three primary tabs preserved |
| Formal counterexample → code bug | **none found** | Honest: no TLC counterexample yet |

## Bypass classification (high-consequence Vultr)

| Path | Class |
|------|-------|
| `compute_provider.VultrComputeProvider` | **BYPASSABLE** inner; **RUNTIME_ENFORCED** when wrapped |
| `shielded_compute` + `GHOSTSHIELD_MODE=ENFORCE` | READY_FOR_M17 (worker API path) |
| `orchestrator.py` golden Vultr | **BYPASSABLE** |
| `scheduler_routes` dry-check | READ-ONLY; not worker create |
| `range-runtime/vultr_adapter.py` | **BYPASSABLE** (world/compute provisioning) |
| Worker cloud-init | No `VULTR_API_KEY` in agent design |

## Tests

| Suite | Result |
|-------|--------|
| `packages/ghostshield/tests` | PASS (P2, TOCTOU revision, ENFORCE deny) |
| `apps/api/tests/test_ghostshield_*` | PASS |
| Live ENFORCE worker lifecycle | **BLOCKING_M17** (Vultr ACL + M16 journal) |

## Agent 52 pre-review

Automatic **NO-GO** triggers still open:

- Alternate Vultr path (`orchestrator`, `range-runtime`) bypasses gateway
- Canonical Postgres `runtime_revision` not authoritative (ephemeral counter in shield wrapper)
- Live ENFORCE acceptance not executed
- Model-check artifacts absent (TLC unavailable locally)
