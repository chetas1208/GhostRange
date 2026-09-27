# Performance budget

| Target | Value |
|--------|--------|
| Desktop FPS | 60 typical, 30 floor |
| Draw calls | prefer hundreds, not thousands |
| DPR | capped 1.5 via PerformanceGovernor |
| React | `frameloop="demand"` + invalidate on events |
| Selectors | no `Object.values` in Zustand selectors (use loops or shallow + useMemo) |
| Bloom | gated — off by default |

Instancing: `InstancedNetworkNodes` where applicable. Adaptive quality: AUTO via PerformanceGovernor (future LOW/BALANCED/HIGH internal).

Audit command: run dev with R3F perf monitor; profile timeline scrub separately.
