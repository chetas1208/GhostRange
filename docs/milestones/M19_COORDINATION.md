# M19 GhostArena — coordination (56 specialists + lead)

Lead agent owns integration; **does not** count toward 56.

| agent_id | mission | owned_paths | hidden_access | evaluation_role | status |
|----------|---------|-------------|---------------|-----------------|--------|
| 01 | M18 audit for eval independence | docs/milestones/M19_AUDIT.md | none | audit | done |
| 02 | Agent eval research | docs/research/M19_GHOSTARENA_SYNTHESIS.md | none | research | partial |
| 03 | Cyber-range benchmark research | docs/research/M19_GHOSTARENA_SYNTHESIS.md | none | research | partial |
| 04 | Statistical evaluation research | packages/ghostarena (stats TBD) | none | design | partial |
| 05 | Arena architecture | docs/architecture/GHOSTARENA.md | read | architect | done |
| 06 | Hidden bundle architect | evaluation/private/, contracts | **write** | evaluator | done |
| 07 | Benchmark isolation | docs/architecture/ARENA_ISOLATION.md, tests | read | engineer | partial |
| 08 | Scenario contract | ghostarena_m19 ArenaScenarioV1 | none | engineer | done |
| 09 | Scenario versioning | ghostarena scenarios | read | engineer | partial |
| 10 | Range templates | (sim only) | read | engineer | stub |
| 11 | Range reset | (sim only) | read | engineer | stub |
| 12 | Range isolation | tests | read | engineer | partial |
| 13 | Procedural scenarios | (future) | **write** | engineer | stub |
| 14 | Scenario validation | verifiers | read | engineer | partial |
| 15 | OutcomeVerifierV1 | ghostarena verifiers | read | verifier | done |
| 16 | ProcessVerifierV1 | ghostarena verifiers | read | verifier | done |
| 17 | SafetyVerifierV1 | ghostarena verifiers | read | verifier | partial |
| 18 | TrajectoryVerifierV1 | ghostarena verifiers | read | verifier | partial |
| 19 | Failure taxonomy | ghostarena_m19 | none | engineer | done |
| 20 | Failure localization | verifiers + FailureLocalizationV1 | read | engineer | done |
| 21 | Failure propagation graph | (contract TBD) | read | engineer | stub |
| 22 | Reward-hacking scenarios | scenarios + verifiers | **write** | engineer | partial |
| 23 | Contamination | (report TBD) | read | engineer | stub |
| 24 | Suite rotation | (policy TBD) | **write** | engineer | stub |
| 25 | Regression suite | scenarios | read | suite | partial |
| 26 | Generalization suite | scenarios | **write** | suite | partial |
| 27 | Adversarial suite | premature-stop-trap | **write** | suite | done |
| 28 | Safety suite | shield-trap | **write** | suite | partial |
| 29 | Reliability suite | (stub) | read | suite | stub |
| 30 | Cost suite | engine cost_delta | read | suite | partial |
| 31 | Drift suite | (stub) | read | suite | stub |
| 32 | Frontier suite | (stub) | read | suite | stub |
| 33 | Causal/transfer suite | (stub) | **write** | suite | stub |
| 34 | Scheduler suite | sched-generalization | **write** | suite | partial |
| 35 | Runtime suite | (stub) | read | suite | stub |
| 36 | Shield suite | shield-trap | read | suite | partial |
| 37 | Evolution suite | self-improve-overfit | **write** | suite | partial |
| 38 | Long-horizon composite | (stub) | **write** | suite | stub |
| 39 | User simulator | (stub) | none | engineer | stub |
| 40 | Trajectory storage | ArenaRunRecordV1 | read | infra | partial |
| 41 | Reproducibility | seed in bundle | read | infra | partial |
| 42 | Statistical comparison | (bootstrap TBD) | none | stats | stub |
| 43 | Cost-normalized eval | release report | read | stats | partial |
| 44 | Capability profile | CapabilityProfileV1 | none | engineer | contract |
| 45 | Release report | GhostArenaReleaseReportV1 | read | engineer | done |
| 46 | GhostEvolve gate | evolve_gate + promotion.py | none | gate | done |
| 47 | Live Vultr arena | (not run) | read | live | **LIVE_ARENA_NOT_RUN** |
| 48 | Multiverse UI | ui-3d/arena/SealedRange | none | ui | partial |
| 49 | Execution UI | ui-3d/arena/ArenaRun | none | ui | partial |
| 50 | Evidence UI | (wire in apps/web TBD) | none | ui | stub |
| 51 | Leakage red team | test_isolation.py | attack | red | partial |
| 52 | Reward-hack red team | test_arena_engine | attack | red | partial |
| 53 | Evaluator bypass red team | promotion tests | attack | red | partial |
| 54 | Statistical integrity reviewer | M19_FINAL | none | review | pending |
| 55 | Research integrity reviewer | synthesis doc | none | review | pending |
| 56 | Independent final reviewer | M19_FINAL GO/NO-GO | none | **final** | **NO-GO** |

**Wave status:** 0–1 foundation landed; 2–6 partial/sim; 7 red-team tests added; 8–9 review **NO-GO**.

**Blockers:** no live Vultr arena; no multi-seed/bootstrap CI; scenarios simulated not multi-host ranges; GhostShield/M18 prerequisites still NO-GO; composite campaign not built.
