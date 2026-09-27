# Tactical UI — implementation report

**Status:** Phase 2 complete for engineering backlog; human UI-30 / 12-screenshot gate remains.

## Completed backlog (this chat)

- [x] Reality audit + architecture + timing model docs
- [x] Shared tactical HUD (header, mission strip, timers, ticker, env badge)
- [x] Multiverse orbital layout + orbit field + discrete fork progress
- [x] Deep links `?tab=&world=&claim=` + cross-tab focus hook
- [x] Task timing partial (`taskTiming` + TaskInspector queue wait)
- [x] `GET /v1/worlds?range_id=` snapshot-derived graph
- [x] `GET /v1/ranges/{id}/timing` benchmark + task event log
- [x] Cost inspector + backend-driven HUD semantics
- [x] Live `cost.snapshot.updated` reducer support
- [x] Compute inspector: billing quantum + NOT OBSERVABLE telemetry
- [x] E2E `tests/e2e/tactical/tactical.spec.ts`
- [x] Screenshot script `scripts/capture-tactical-ui.mjs` (run when preview up)

## Explicitly not done (requires human or provider data)

- [ ] UI-30 / UI-28 human sign-off
- [ ] Real CPU/RAM/GPU telemetry (provider adapter)
- [ ] Historical P50 timing store
- [ ] World comparison UI
- [ ] Full tactical screenshot set (12 PNGs) — run capture script locally
- [ ] Full §94–99 completion gate sign-off document

## How the three tabs work

| Tab | Source of truth |
|-----|-----------------|
| MULTIVERSE | SSE worlds/forks/workers + orbital scene |
| EXECUTION | Task DAG events + timing route + inspectors |
| EVIDENCE | Claims/artifacts events + DOM inspectors |

## Tests

```bash
npm run typecheck
npm run test -w apps/web
npm run test:e2e:tactical   # needs preview + API or fixture bootstrap
```

## HACP / Claude non-clash

Did **not** modify HACP peer-A owned paths: `apps/web/package.json`, `docs/ui/THREE_D_ARCHITECTURE.md`, `packages/ui-3d/package.json`.
