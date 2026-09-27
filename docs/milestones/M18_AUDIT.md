# M18 Audit — Wave 0 (2026-09-27)

## Prerequisites

| Milestone | Status | M18 impact |
|-----------|--------|------------|
| M16 durable replay | **NO-GO** | Experience partially **NON_REPLAYABLE** |
| M17 ENFORCE + non-bypass | **NO-GO** | Promotion uses GhostShield; live promotion **BLOCKING_M18** |
| Real worker history volume | **INSUFFICIENT_DATA** | Synthetic + mock worker durations in tests |

**Rule:** No automatic production promotion until M16/M17 GO.

## Experience readiness

| Asset | Class |
|-------|-------|
| Worker benchmark outcomes | REAL_PARTIAL |
| GhostLedger full lineage | REAL_PARTIAL |
| Scheduler decision logs | REAL_PARTIAL |
| Fixture campaigns | **UNSAFE_TO_LEARN_FROM** if unlabeled |
| GhostShield denials | READY_FOR_LEARNING (near-miss) |

## GhostEvolve code (Wave 0–1)

| Component | Class |
|-----------|-------|
| `ghostevolve_m18` contracts | READY_FOR_LEARNING |
| `GhostExperienceStore` | REAL_PARTIAL (in-memory + optional file) |
| Eligibility filter | REAL_PARTIAL |
| Runtime estimator champion/candidate | REAL_PARTIAL |
| Temporal eval + regression | REAL_PARTIAL |
| `EvolutionPromotionGate` | REAL_PARTIAL |
| Postgres experience store | **STUB** |
| Shadow/canary runtime wiring | **SIMULATED** |
| Director ranking learner | **NOT_STARTED** |

## Automatic promotion

**Disabled** — human approval + GhostShield required; registry does not auto-write production config.
