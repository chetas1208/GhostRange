# M10 System Architecture — One Product

GhostRange is a **single pipeline** with two planners:

```
Knowledge ──▶ GhostDirector (WHAT) ──▶ ExperimentExecutionDAGV1
                                              │
                                              ▼
                                    GhostScheduler (HOW) ──▶ Tasks / workers
                                              │
                                              ▼
                                    Disposable worlds (Vultr or mock provider)
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
              Verification            Adversarial search           Evidence
                    │                         │                         │
                    └─────────────────────────┴──────────▶ GhostLedger ──▶ Bundle
```

## Integration package boundaries (no new subsystem)

| Layer | Location |
|-------|----------|
| Golden path orchestration | `apps/api/ghostrange_api/golden_path.py` |
| M2 world runtime | `apps/api/ghostrange_api/orchestrator.py` |
| Director | `packages/ghostdirector` |
| Scheduler V3 | `packages/scheduler` |
| Compiler | `packages/range-compiler` |
| Ledger | `packages/ghostledger` |
| Adversarial | `packages/adversarial-verifier` |
| UI | `apps/web` (LIVE / RECORDED_LIVE / FIXTURE) |

## Data sources for UI (M10)

1. **LIVE** — API SSE + snapshot  
2. **RECORDED_LIVE** — JSONL from successful run (future)  
3. **FIXTURE** — static replay for dev/demo  

## Live guard

`GHOSTRANGE_LIVE=true` AND credentials required for provider truth. Default dev/mock must not provision.
