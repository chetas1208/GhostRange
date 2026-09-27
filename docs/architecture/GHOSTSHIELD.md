# GhostShield architecture (M17)

```
GhostDirector / GhostScheduler  (UNTRUSTED proposers)
        │
        ▼
  CanonicalActionV1
        │
        ▼
  GhostShieldPolicyEngine  (TRUSTED)
        │
   ALLOW / DENY / STATE_STALE / …
        │
        ▼
  ActionPermitV1 (short-lived, digest-bound)
        │
        ▼
  GhostExecutionGateway  (TRUSTED)
        │
        ▼
  VultrComputeProvider (inner) / Mock
```

**TCB:** policy engine, gateway, canonical Postgres (when wired), versioned policy bundle.

**Not in TCB:** LLM, UI, Director, Scheduler.

**Modes:** `GHOSTSHIELD_MODE` = `DISABLED` | `SHADOW` | `ENFORCE` | `LOCKDOWN`.

Worker billable path: `build_compute_provider()` wraps inner provider with `ShieldedComputeProvider` unless `DISABLED`.
