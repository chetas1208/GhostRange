# M20 UI acceptance coordination (30 specialists)

**Campaign:** M20 UI Acceptance Closure — **no visual redesign.**

**UI-30 status:** **UI-NO-GO** pending UI-28/29 human review (automation green in Docker as of last run).

| agent_id | mission | status | notes |
|----------|---------|--------|-------|
| UI-01 | Audit locked UI | done | |
| UI-02 | Live event inventory | done | `M20_LIVE_EVENT_INVENTORY.md` |
| UI-03 | SSE transport | done | `campaignStream.ts` |
| UI-04 | Bootstrap/replay | done | snapshot→SSE |
| UI-05 | Idempotency / OOO | done | tests + `releasedWorkerIds` |
| UI-06 | Campaign phase | done | |
| UI-07 | Multiverse mapping | done | fork + attack via `m20_ui_events` |
| UI-08 | Execution DAG | done | M2 stream |
| UI-09 | Worker lifecycle | done | |
| UI-10 | Scheduler visuals | done | decision + plan |
| UI-11 | Causal visuals | done | reducer + backend emit |
| UI-12 | Runtime failure/recovery | done | simulated durable events |
| UI-13 | Shield gate/deny | done | `execution.denied` |
| UI-14 | Evidence | done | M2 + claims |
| UI-15 | Arena | done | campaign.phase |
| UI-16 | Timeline/history | done | `liveEventBuffer` |
| UI-17 | Camera states | partial | named states only |
| UI-18 | React #185 audit | ongoing | primitive selectors |
| UI-19 | Performance | done | `collect-m20-ui-perf.mjs` |
| UI-20 | A11y E2E | done | keyboard + reduced-motion |
| UI-21 | Golden E2E | done | `golden-path.spec.ts` |
| UI-22 | SSE reconnect | done | `sse-reconnect.spec.ts` |
| UI-23 | Semantic capture | done | `capture-m20-ui.mjs` |
| UI-24 | Visual regression | done | `visual-core.spec.ts` |
| UI-25 | Capture env | done | docker script |
| UI-26 | Browser matrix | partial | ff/webkit smoke |
| UI-27 | Fixture contamination | done | `m20-ui-fixture-audit.mjs` |
| UI-28 | Visual quality review | pending | human |
| UI-29 | Release E2E review | pending | human |
| UI-30 | Final UI-GO/NO-GO | **NO-GO** | awaits UI-28/29 sign-off |

## Commands

```bash
make ui-acceptance
# or (recommended on hosts missing libasound):
bash scripts/m20-ui-acceptance-docker.sh
```

## Artifacts

- `artifacts/screenshots/ui-final/` — 24 PNG + `manifest.json` + `index.html`
- `artifacts/e2e/reports/`
- `artifacts/performance/m20-ui-performance.json`
