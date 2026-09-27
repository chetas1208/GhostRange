# Tactical UI — performance

## Budgets (inherit M20)

See [PERFORMANCE_BUDGET.md](./PERFORMANCE_BUDGET.md) and [THREE_D_ARCHITECTURE.md](./THREE_D_ARCHITECTURE.md).

| Target | Value |
|--------|--------|
| Frame rate | 60 FPS nominal on dev workstation |
| Canvas | `frameloop="demand"` + `useInvalidateOnEvents` |
| DPR cap | `PerformanceGovernor maxDpr={1.5}` |
| Live events | Buffer capped at 1200 (`store.dispatchEvents`) |
| Log/ticker DOM | Slice last N entries (EventTicker: 8) |

## Tactical additions

- Multiverse orbit: single `useFrame` on one group — stop when `--gr-motion-scale: 0`.
- Avoid per-event React re-render: primitive Zustand selectors.
- Future: instancing for large worker fleets; LOD for world interior.

## Measurement (local)

- `scripts/collect-m20-ui-perf.mjs` — CDP stub from M20 acceptance.
- Re-run after tactical scenes grow; record FPS / draw calls here when captured.

## Stress scenarios (planned)

- Rapid tab switch
- 1000+ SSE events burst
- Replay scrub during live
