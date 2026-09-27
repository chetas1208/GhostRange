# World lineage — canonical base vs derived worlds

## Terms

- **Canonical base world** — the world where the controlled incident was reproduced; treated immutable for remediation after fork point `T0`.
- **Derived / remediation world** — child created by `world.forked`; owns one `RemediationPlanV1` application and its verification/evidence scope.
- **Historical world** — pruned or destroyed branch; remains in persistence (`HistoricalWorldV1`) and Evidence mode; Multiverse may collapse geometry.

## Lineage graph

```text
Range
 └── Base World (root)
       ├── Fork → World A (Remediation A)
       ├── Fork → World B (Remediation B)
       └── Fork → World C (Remediation C)
```

Nested forks (World B → B1) are **allowed by contracts** (`fork_generation`) but **not required in M3**.

## Persistence

| Record | Purpose |
|--------|---------|
| `WorldV1` | Lifecycle status per node |
| `WorldForkV1` | Legacy/minimal fork edge (M1/M2) |
| `WorldForkV2` | M3 fork metadata + fingerprint |
| `WorldFingerprintV1` | Prove comparable starting state |
| `HistoricalWorldV1` | Post-prune audit bundle |

## Isolation rules

1. Evidence artifacts keyed by `(range_id, world_id, content_hash)`.
2. Remediation actions may only target assets registered to **that** `world_id`.
3. Scheduler decisions scoped to `(world_id, task_id)`; branch prune stops new tasks for that world only.
4. Teardown destroys provider resources tagged with GhostRange ownership for that `world_id` only.

## Events (M3 target)

- `world.fork_requested` → `world.forked` → provisioning → `world.ready`
- Remediation: `remediation.applied` (typed actions)
- Verification: shared `VerificationSuiteV1` per candidate
- End: `world.pruning` → `world.pruned` / `world.destroyed`

See `docs/milestones/M3_COORDINATION.md` Agent 19 for full event catalog.
