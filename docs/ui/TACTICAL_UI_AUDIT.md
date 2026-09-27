# Tactical 3D UI — Reality Audit

**Date:** 2026-09-27  
**Branch:** `master` (no commits yet; entire tree untracked)  
**Local revision:** working tree only — **DEPLOYED_UNVERIFIED** (health probe to `127.0.0.1:8000` returned 404; API not running at audit time)

## Executive summary

GhostRange already ships **exactly three primary modes** (MULTIVERSE | EXECUTION | EVIDENCE) via `ModeSelector`, a single shared R3F canvas (`GhostCanvas`), snapshot+SSE live transport (`campaignStream.ts`), and M20 golden-path orchestration with UI accent events. The product is **not** a blank slate: most 3D semantics are **event-reducer driven** and documented in `LIVE_STATE_MAPPING.md`.

Gaps for the tactical campaign are concentrated in:

- **Operation-level timing contract** (`OperationV1` / queue wait / estimate source) — partial at orchestrator benchmark, not on every UI entity.
- **Server telemetry** (CPU/RAM/GPU/network) — **NOT OBSERVABLE** in UI; only lifecycle + cost/hr from events.
- **World REST graph** (`GET /v1/worlds/*`) — **NOT_IMPLEMENTED**; worlds arrive only via SSE/snapshot events.
- **Fake-adjacent visuals** — fork branch `progress` uses discrete lifecycle heuristics (not arbitrary % bars); worker `utilization` may animate without provider metrics.
- **Cross-tab URL context** — **REAL_LIVE** (`useTacticalSelectionUrl` + `useCrossTabFocus`).
- **Dedicated tactical HUD** — **PARTIAL** (composed from existing `ProductIdentity`, `SystemStatus`, inspectors); extended in Phase 1.

## Test baseline (audit run)

| Command | Result |
|---------|--------|
| `npm run typecheck` | **PASS** |
| `npm run test -w apps/web` | **9 passed**, 0 failed |
| `pytest apps/api/tests` | **31 passed**, 4 skipped |
| `pytest -q --ignore=packages/range-runtime/tests/test_persistence.py` | **777 passed**, **9 failed** (Postgres event-store persistence tests; env DB) |

Do **not** trigger GitHub Actions per project policy.

## Primary navigation

| Feature | Classification | Notes |
|---------|----------------|-------|
| Three tabs only | **REAL_LIVE** | `ModeSelector.tsx` — keys 1/2/3 |
| `ModeDock.tsx` | **STATIC_UI / UNUSED** | File exists; not mounted in `AppShell` |
| Extra primary tabs (Dashboard, Fleet, …) | **NOT_IMPLEMENTED** | Correct |

## Data transport

| Feature | Classification | Notes |
|---------|----------------|-------|
| Fixture JSONL replay | **REAL_LOCAL** | `VITE_DATA_SOURCE=fixture`, M1/M2 fixtures |
| SSE `/v1/ranges/{id}/stream` | **REAL_BACKEND_DERIVED** | After snapshot |
| Snapshot `/v1/ranges/{id}/snapshot` | **REAL_BACKEND_DERIVED** | Authoritative replay buffer seed |
| Event dedup / seq | **REAL_LIVE** | `campaignStream.ts`, `processedEventIds` |
| Reconnect | **PARTIAL** | Re-snapshot + resubscribe; UI shows OFFLINE when disconnected |
| Postgres gap heal | **BROKEN** (local) | 9 failing persistence tests without DB |

## Connection / environment labeling

| HUD label | Classification | When |
|-----------|----------------|------|
| `● LIVE` | **REAL_LIVE** | `dataSource=live` && `streamConnected` |
| `○ OFFLINE` | **REAL_LIVE** | Live mode, stream down — no invented state |
| `◇ SIMULATED` | **REAL_LOCAL** | Fixture replay |
| `◷ HISTORY` | **REAL_BACKEND_DERIVED** | Timeline scrub (fixture or live buffer) |
| `◇ CONTROLLED REPLAY` | **SIMULATED** | Product tour fixture |
| Provider badge MOCK/VULTR | **REAL_BACKEND_DERIVED** | From `compute.*` payloads only |

## Tab 1 — MULTIVERSE

| Feature | Classification | Notes |
|---------|----------------|-------|
| World capsules + network graph | **REAL_BACKEND_DERIVED** | After `world.ready` / asset events |
| Provisioning shell | **REAL_BACKEND_DERIVED** | `world.provisioning` |
| Fork lineage (`HypothesisBranch`) | **REAL_BACKEND_DERIVED** | From `forks[]` + world records |
| Fork line progress (0.2 / 0.55 / 1) | **REAL_BACKEND_DERIVED** | Discrete lifecycle encoding, **not** measured % |
| World layout positions | **STATIC_UI** → **PARTIAL** | Fixed offsets; Phase 1 orbital layout |
| Slow orbit motion | **SIMULATED** | Decorative drift; disabled under reduced motion |
| Attack paths | **REAL_BACKEND_DERIVED** | M20 `attack.*` events when emitted |
| Production shadow | **SIMULATED** | Promotion preview overlay |
| LOD / zoom levels | **PARTIAL** | Camera levels + wheel; no full topology LOD |
| Time scrubber | **REAL_BACKEND_DERIVED** | `TimelineBar` + live buffer |
| World comparison delta | **NOT_IMPLEMENTED** | |
| Server objects in multiverse | **REAL_BACKEND_DERIVED** | `ComputeNode` from worker state |
| CPU/RAM on servers | **NOT_IMPLEMENTED** | Inspector shows class/region/cost only |

## Tab 2 — EXECUTION

| Feature | Classification | Notes |
|---------|----------------|-------|
| Scheduler DAG / tasks | **REAL_BACKEND_DERIVED** | `ExecutionScene`, task events |
| GhostDirector decisions | **PARTIAL** | Golden path / M20 events; not full Director UI contract |
| GhostScheduler WHY panel | **REAL_BACKEND_DERIVED** | `DecisionInspector`, `scheduler.decision` |
| Speculative split / blocked edges | **REAL_BACKEND_DERIVED** | Reducer + scene |
| Live timers per stage | **PARTIAL** | Campaign elapsed from events; benchmark API for decomposition when run active |
| Queue wait visibility | **NOT_IMPLEMENTED** | No `queued_at` on tasks in store |
| Retries history | **PARTIAL** | Some verification/health narrative in events; no unified retry panel |
| Resource HUD (CPU alloc, GPU) | **NOT_IMPLEMENTED** | Worker counts + cost only |
| Server queue view | **NOT_IMPLEMENTED** | |
| Log drawer | **PARTIAL** | `eventLog` / detail surfaces; not full virtualized log tail |
| Cancel / destroy controls | **PARTIAL** | Command palette / API where wired; GhostShield bounded |

## Tab 3 — EVIDENCE

| Feature | Classification | Notes |
|---------|----------------|-------|
| Provenance constellation | **REAL_BACKEND_DERIVED** | Artifacts, claims, verification ring |
| Claim inspector | **REAL_BACKEND_DERIVED** | `EvidenceInspector` |
| Counterexample / adversarial budget | **PARTIAL** | M20 counterexample events when run |
| Promotion lineage in-tab | **PARTIAL** | `promotion` summary state; no Promotion tab |
| GhostWatch / Mesh / Causal | **SIMULATED** | Summary overlays; milestones NO-GO |
| Claim timeline replay | **PARTIAL** | Scrub affects global replay, not claim-only |
| 2D-readable evidence | **REAL_LIVE** | DOM inspectors primary for text |

## 3D / interaction stack

| Component | Classification |
|-----------|----------------|
| React Three Fiber canvas | **REAL_LIVE** |
| `@react-three/drei` OrbitControls | **REAL_LIVE** |
| `CameraRig` presets | **PARTIAL** |
| Object picking → inspectors | **REAL_LIVE** |
| Reduced motion (`--gr-motion-scale`) | **REAL_LIVE** |
| Idle camera drift | **NOT_IMPLEMENTED** (orbit drift added for multiverse field only) |

## Backend APIs (tactical needs)

| Route / contract | Status |
|------------------|--------|
| `/v1/ranges/{id}/snapshot`, `/stream` | **REAL_LIVE** |
| `/v1/ranges/{id}/benchmark` | **REAL_BACKEND_DERIVED** | RunBenchmark decomposition (mock/live run) |
| `GET /v1/worlds?range_id=` | **REAL_BACKEND_DERIVED** (event fold) |
| `GET /v1/ranges/{id}/timing` | **PARTIAL** (benchmark + task events; no P50 DB) |
| `OperationTimingV1` / historical P50 | **PARTIAL** (`taskTiming` in store; P50 **NOT_IMPLEMENTED**) |
| Vultr instance metrics | **NOT OBSERVABLE** unless live worker telemetry added |

## Cost

| Source | Classification |
|--------|------------------|
| `totalCostUsd` in store | **REAL_BACKEND_DERIVED** | From events / reducer |
| `CostIndicator` HUD | **REAL_BACKEND_DERIVED** |
| Per-category cost split | **NOT_IMPLEMENTED** |
| Unknown pricing | Must show **UNKNOWN** — never $0.00 fiction |

## M20 acceptance artifacts

| Artifact | Status |
|----------|--------|
| Playwright `tests/e2e/ui-final/` | **REAL_LOCAL** (5/5 passed in prior Docker run) |
| 24 screenshots `artifacts/screenshots/ui-final/` | **REAL_LOCAL** |
| UI-30 human sign-off | **NOT_IMPLEMENTED** |

## Deployment reality

| Environment | Classification |
|-------------|----------------|
| Local repository | **LOCAL_IMPLEMENTED** |
| Production / Vultr deploy | **DEPLOYED_UNVERIFIED** at audit time |
| Live Vultr workers | **REAL_LIVE** when `GHOSTRANGE_LIVE=true` + credentials |

## Recommended implementation order

1. Shared tactical HUD + honest timers (event timestamps + `/benchmark` when available).
2. Multiverse orbital layout + lineage clarity (no fake progress bars).
3. Backend `OperationTimingV1` adapter + history store (reuse orchestrator + event log).
4. Server inspector telemetry sections (NOT OBSERVABLE until provider adapter exists).
5. Evidence temporal claim graph + E2E tactical scenario + 12 screenshots (`artifacts/screenshots/tactical/`).

See `TACTICAL_UI_ARCHITECTURE.md`, `REALTIME_TIMING_MODEL.md`.
