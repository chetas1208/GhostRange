# GhostArena (M19)

GhostArena is the **independent evaluation substrate** for GhostRange. GhostEvolve may consume **sanitized** `GhostArenaReleaseReportV1` summaries; it must not read `ArenaHiddenBundleV1` or active hidden seeds.

## Boundary

```text
GHOSTRANGE_RUNTIME (apps/api, worker, evolve training)
        │
        │ candidate + baseline traces (no hidden GT)
        v
   GhostArenaEngine  ←── evaluation/private/ (ArenaHiddenStore)
        │
        v
 GhostArenaReleaseReportV1  ──► EvolutionPromotionGate (PRODUCTION only)
```

## Core types

- `ArenaScenarioV1` — public instruction, budgets, family, suite type.
- `ArenaHiddenBundleV1` — seed, ground truth, hidden verifier spec (evaluator only).
- Verifiers: outcome, process, safety, trajectory.
- `FailureLocalizationV1` — first material deviation.
- `GhostArenaReleaseReportV1` — capability/safety/cost deltas, `QUALIFIED | NOT_QUALIFIED | INSUFFICIENT_EVIDENCE`.

## Demo path (simulated)

1. Candidate `stopping-policy:v6` with `fast_premature` policy — visible speed/cost win.
2. Hidden process verifier — cancelled branch B → `PREMATURE_STOP` → **NOT_QUALIFIED**.
3. Candidate `runtime-estimator:v7` with `qualified` policy → **QUALIFIED** → promotion allowed when human + GhostShield pass.

Package: `packages/ghostarena/`.
