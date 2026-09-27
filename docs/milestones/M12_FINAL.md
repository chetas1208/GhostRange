# M12 Final — GhostWatch

**Agent 38 verdict: NO-GO** (foundation + simulator; M11 blockers partially inherited)

## M11 blockers — inherited vs closed

| Blocker | Closed? |
|---------|---------|
| Exact-patch recompile | **Partial** — local Range Compiler via `verify_proposed_patch`; not live Vultr |
| Live Vultr promotion worlds | **No** — use simulator |
| GhostLedger promotion lineage | **Partial** — in-memory lineage bridge; not full M7 seal |
| M11 screenshots / Agent 32 GO | **No** |

M12 does **not** claim M11 is complete.

## What is GhostWatch?

Post-approval **observation and deterministic rollout evaluation** boundary. It closes the evidence loop after an external executor applies an approved change.

## Production authority

| Mode | Meaning |
|------|---------|
| `OBSERVE_ONLY` | **Default** — no control requests |
| `RECOMMEND` | Emit advance/hold/rollback recommendations |
| `PREAUTHORIZED_PAUSE` | Adapter may pause if capability exists |
| `PREAUTHORIZED_ROLLBACK` | Exact rollback digest only |

Models/Director/Scheduler **cannot** escalate.

## What works now

- M12 contracts (`ghostwatch_m12.py`)
- `GhostWatch` campaigns + conformance + canary analysis
- `ProductionRolloutSimulator` (`SIMULATED_ROLLOUT`)
- Mock executor adapter
- API simulate + campaign start
- Benchmark script (`unsafe_advance_count=0` target on corpus)
- Director disposable experiment proposal from surprise

## Gaps

- Argo Rollouts controlled-live adapter
- Prometheus/OTEL real adapter
- GhostLedger full rollout event stream
- Living Twin write-back
- UI screenshots (12)
- Feature flag adapter (OpenFeature-shaped stub only)

## M13 — GhostMesh started

See `docs/milestones/M13_FINAL.md` (Agent 40 **NO-GO**; simulated 5-node harness).

## Integrity language

Observation attestation ≠ production safety proof.
