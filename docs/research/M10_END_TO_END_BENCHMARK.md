# M10 End-to-End Benchmark (mock golden path)

**Mode:** simulation (no Vultr charges)

**Environment:** local `.venv`, `GoldenPathOrchestrator.run()` on auth-lab compose

## Sample run (representative)

| Metric | Approx value |
|--------|----------------|
| total_wall_time_ms | 50–200 |
| compile_ms | 10–80 |
| director_ms | 5–20 |
| scheduler_ms | 1–5 |
| adversarial_ms | 5–30 |
| ledger_ms | 5–15 |
| bundle_verified | true |
| counterexamples_confirmed | 0–1 |

## Baseline comparison

Not yet run: **STATIC_SERIAL** vs **GHOSTDIRECTOR+GHOSTSCHEDULER** on same scenario (backlog).

## Honesty

Mock path does not measure provision_ms, teardown_ms, or live orphan rate.
