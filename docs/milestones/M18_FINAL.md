# M18 GhostEvolve — final report (Agent 54)

**Decision: NO-GO** (2026-09-27)

## What is GhostEvolve?

Controlled pipeline from **verified** experience to **versioned candidates** on explicit learning surfaces, with offline evaluation, regression, shadow, human approval, and GhostShield-gated promotion.

## What counts as experience?

`ExperienceRecordV1` after provenance/safety/eligibility — not raw chat or unverified fixtures.

## Rejected / quarantined

Corrupted provenance, poison tags, fixture masquerading as real, unsafe outcomes.

## Storage

In-memory/file `GhostExperienceStore` v1 — **Postgres + Object Storage not wired**.

## Learning surfaces

Contract enumerates 13 surfaces; **implemented trainer:** `SCHEDULER_RUNTIME_ESTIMATOR` only.

## Forbidden surfaces

GhostShield hard invariants (enforced in policy engine on `PROMOTE_EVOLUTION_CANDIDATE`).

## First improvement attempt

Runtime EWMA candidate vs M15 inflation champion on synthetic temporal splits — **unit PASS**; real worker corpus **INSUFFICIENT_DATA**.

## Future leakage

`temporal_train_test_split` — past train, future test.

## Baseline / candidate

`runtime-estimator:v4-m15` vs `runtime-estimator:v5` (EWMA).

## Improved / regressed

Tests: future MAE improves on cpu_benchmark series; bad bursty challenger worse than champion on old slice.

## Catastrophic forgetting

Measured via old-workload holdout delta in `RegressionResult` / `ForgettingReportV1` — **partial**.

## Shadow / canary

Shadow UI components only; **live canary NOT RUN** (`CANARY_NOT_RUN`).

## Promotion authorization

Human `approval_digest` required; GhostShield `PROMOTE_EVOLUTION_CANDIDATE`; digest swap blocked.

## Can model promote itself?

**No** — REQUIRE_HUMAN without approval.

## Can learner change GhostShield?

**No** — DENY if learning_surface implies invariant mutation.

## Rollback

Registry preserves champion history; `rollback_to` requires version in history.

## Revoked experience

**TAINTED** lineage — not fully implemented (M19).

## Costs / amortization

Not measured live.

## Rejected candidates

Regression gate rejects slice-regression scenarios in tests.

## NO-UPDATE wins

Valid when `INSUFFICIENT_DATA` or regression fails.

## Agent 54 automatic NO-GO

- M17 ENFORCE not verified
- No production promotion executed
- Catastrophic forgetting not end-to-end on real corpus
- Shadow candidate could not be validated live
- Postgres experience store absent

## M19 should

1. Ingest real worker benchmark durations into experience store.
2. Wire shadow runtime predictions on live scheduler (read-only challenger).
3. Persist promotion lineage in GhostLedger.
4. Complete M17 GO then canary runtime estimator on live campaigns.
5. Startup-latency estimator as second surface.
