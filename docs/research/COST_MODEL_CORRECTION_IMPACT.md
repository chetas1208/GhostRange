# Cost model correction impact

## Material change

**Old:** `cost ≈ hourly_rate × (seconds / 3600)`  
**New:** `cost ≈ ceil(lifetime_seconds / 3600) × hourly_rate` (minimum 1 hour when lifetime > 0), per pinned Vultr policy.

## Example (Acceptance A)

- Rate **P = $0.10/hr**  
- Lifetime **7 minutes** (420 s)

| Model | Cost |
|-------|------|
| Per-second | $0.00117 |
| One-hour minimum | **$0.10** |

Underestimation factor ≈ **85×** for this scenario.

## Scheduler implications (qualitative)

| Scenario | Old tendency | Corrected tendency |
|----------|--------------|-------------------|
| Spawn short worker for 5 min task | Cheap | **Whole hour committed** |
| Reuse worker in same hour | Same as new | **Prefer reuse** (low incremental) |
| Speculative second VM | Undercount loser | **Both quanta count** |
| Scale-in at 30s idle | Destroy looks cheap | May keep within sunk quantum |
| Parallel vs serial | Favors parallel | Serial on one VM may be cheaper |

## Benchmarks

Re-run `packages/scheduler` benchmarks after rate cards bind to real plan prices. **Decision changes are expected** — do not revert math for demo stability.

## Quantification (scheduler benchmark cases)

From `python scripts/benchmark_scheduler_cost_quantum.py` (CPU_MEDIUM @ $0.03/hr):

| Task type | Duration | Legacy USD | Quantum USD | Ratio |
|-----------|----------|------------|-------------|-------|
| INVESTIGATE | 300s | 0.0025 | 0.03 | 12× |
| VERIFY | 120s | 0.0010 | 0.03 | 30× |
| ATTACK | 600s | 0.0050 | 0.03 | 6× |
| ANALYZE | 1800s | 0.0150 | 0.03 | 2× |

Short tasks were **under-costed** by an order of magnitude under per-second billing.
