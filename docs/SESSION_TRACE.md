# Cross-session trace (Cursor + Claude / HACP)

**Generated:** 2026-09-27  
**Purpose:** Single map of what each session promised, what landed, and what remains.

## Agent transcripts

| Session | Transcript ID | Primary arc |
|---------|---------------|-------------|
| GhostRange UI (Claude peer A) | [82821b6f…](82821b6f-8bd8-47f4-876d-aad24307b7a5) | M1 UI shell, HACP start, EVENTS_CONTRACT, fixture, ui-3d tree |
| Cursor (this thread) | Same + continuations | M20 live SSE, tactical 3-tab UI, cost accounting quantum |

Read transcript: search keywords (`M20`, `tactical`, `cost`, `TOUR`, `HACP`).

## HACP coordination

| Item | Status |
|------|--------|
| Peer A started | `.hacp/session.json` — owns `apps/web/package.json`, `THREE_D_ARCHITECTURE.md`, `ui-3d/package.json` |
| Peer B join | **Never joined** — backend built without dual-peer lock |
| Terms file | `docs/ui/hacp-terms-events.json` |
| Event catalog (Peer B deliverable) | **`packages/events/ghostrange_events/catalog.py`** (added 2026-09-27) |
| HACP acceptance terms | **`docs/ui/hacp-terms-events.json`** — catalog + SSE transport updated 2026-09-27 |
| Non-clash rule | Cursor cost/tactical work avoided HACP-owned paths |
| UI spec gap audit (subagent) | Transcript subagent `de47b3fe…` — §42 partial; tactical/M20 work addressed many wiring gaps; external §1–44 lock still not in repo |

See `docs/ui/HACP_STATUS.md`.

## Claude / M1 UI session — engineering closure

| Deliverable | Status |
|-------------|--------|
| `apps/web` + `packages/ui-3d` | **Done** |
| `docs/ui/UI_SPECIFICATION` / FINAL specs | **Done** (see `docs/ui/FINAL_*`) |
| `docs/ui/EVENTS_CONTRACT.md` | **Done**; transport is SSE not WS |
| Fixture replay | **Done** |
| Peer B `packages/events` store | **Partial** — Postgres gateway exists; not default API path |

## M20 UI acceptance (multi-agent UI-01…30)

| Gate | Status |
|------|--------|
| Automation (E2E, 24 screenshots, Docker) | **Green** (last documented Docker run) |
| UI-28 / UI-29 human review | **Pending human** |
| UI-30 GO | **NO-GO** until UI-28/29 |

Ref: `docs/milestones/M20_UI_ACCEPTANCE_COORDINATION.md`, `docs/ui/FINAL_SCREENSHOT_ACCEPTANCE.md`.

## Tactical 3-tab UI campaign

Ref: `docs/ui/TACTICAL_UI_FINAL.md`, `docs/ui/TACTICAL_UI_AUDIT.md`.

| Item | Status |
|------|--------|
| Audit + architecture docs | **Done** |
| HUD, orbit multiverse, URL sync | **Done** |
| Worlds API (snapshot fold) | **Done** — `GET /v1/worlds?range_id=` |
| Timing partial | **Done** — `taskTiming` + `/v1/ranges/{id}/timing` |
| Cost inspector + SSE snapshot | **Done** |
| Tactical E2E | **Done** — `npm run test:e2e:tactical` |
| 12 tactical PNGs | **Script** — `scripts/capture-tactical-ui.mjs` (run when preview up) |
| Full §94–99 sign-off | **Human / live campaign** |

## Cost accounting campaign

Ref: `docs/milestones/M20_COST_ACCOUNTING_FINAL.md`, `docs/architecture/COST_ACCOUNTING_AUDIT.md`.

| Item | Status |
|------|--------|
| `ghostrange-cost` package + tests | **Done** |
| Scheduler quantum + warm retention helper | **Done** |
| Orchestrator ledger + `cost.snapshot.updated` | **Done** |
| Inference token metering | **Done** when `usage` present |
| Postgres durable ledger | **SQL stub** — `packages/cost/sql/001_cost_ledger.sql` |
| Provider invoice reconciliation | **Open** |

## Interactive tour (TOUR-20)

Ref: `docs/product/INTERACTIVE_TOUR.md`.

| Item | Status |
|------|--------|
| Engine + guided/judge/technical steps | **Done** |
| History step in `guidedSteps.ts` | **Done** (replay at 20s) |
| Explore mode entry | **Done** (`tourStore.exploreMode`) |
| E2E basic | **Done** — `tests/e2e/tour/tour.spec.ts` |
| Tour screenshots | **Script** — `scripts/capture-tour-screenshots.mjs` |
| TOUR-20 human GO | **NO-GO** until screenshots + review |

## M2 backend session (Claude) — follow-ups closed here

| Item | Status |
|------|--------|
| `list_worlds()` untagged leak | **Fixed** (real + mock providers) |
| `list_computes()` ownership | Was fixed prior |
| Live golden campaign POST | **Blocked on user/live creds** (documented in M2_INTEGRATION_STATUS) |

## Master backlog

50+ workstreams in `docs/BACKLOG.md` — mostly M3–M6 **open** by design. Not in scope for a single closure pass.

## Commands to verify this trace

```bash
make install-py
pytest -q packages/vultr-control/tests packages/range-runtime/tests packages/cost/tests
pytest -q apps/api/tests/test_cost_bridge_sse.py apps/api/tests/test_mock_m2_e2e.py
npm run typecheck && npm run test -w apps/web
python scripts/benchmark_scheduler_cost_quantum.py
# or full gate: make test
```

## Release evidence pass (2026-09-27)

See `docs/milestones/M20_RELEASE_EVIDENCE.md` — Postgres cost ledger, reconciliation API, timing samples, tactical cost E2E, capture scripts. Live JSON evidence under `artifacts/release-evidence/`. Redeploy control VM to activate on production.

## What only a human can close

- UI-30, TOUR-20, M10/M11–M19 milestone NO-GO gates
- Live Vultr golden + 24-frame acceptance on production
- Git first commit (user requested deferral)
- Real provider invoice reconciliation
