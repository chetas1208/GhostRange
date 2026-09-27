# M20 release evidence + observability closure

**Scope:** Proof only — no new product subsystems.

## Correction (2026-09-27, later same day)

This file originally described the 12 tactical screenshots as captured from a "live golden campaign" and
the run recorded in `artifacts/release-evidence/m20-live-campaign.json` (see "Live run" section below) as
a successful "~4.5 min" real live run. Neither claim survives checking the artifact itself:

- `m20-live-campaign.json` records `elapsed_ms: 5747` (5.7 seconds, not ~4.5 minutes), `campaign.phase:
  "FAILED"`, `live_worker_outcome: "not_attempted"`, `errors: ["live teardown must use coordinated lease +
  vultr-control", "worker_benchmark:RuntimeError"]`, `timing.benchmark_decomposition.live_provider:
  "mock"`, and `cost.total_known_usd_micros: 0` with `reconciliation.status: "PROVIDER_UNAVAILABLE"`. It
  was a real HTTP 200 against the real public URL with `live_mode="live"`, but the campaign failed before
  any live worker step ran — it is not evidence of a completed live golden campaign.
- The 12 screenshots (`artifacts/screenshots/tactical/manifest.json`) were captured from that same failed
  run: every frame carries `"backend_cost_micros": 0` and `"reconciliation_status": "PROVIDER_UNAVAILABLE"`.
  They are real Playwright/Chromium screenshots of a real page render — the capture mechanism itself
  works — but of a non-real-infra, failed run, not of a live golden campaign.

The real M20 golden campaign triggering live Vultr worker creation as one integrated run has still never
completed successfully. This remains the single biggest gap between what's built and what's proven as one
real run — see `docs/release/M20_REALITY_MATRIX.md` and `docs/milestones/M20_FINAL.md`.

## Acceptance checklist

| Gate | Target | Status |
|------|--------|--------|
| Tactical screenshots | 12 / 12 in `artifacts/screenshots/tactical/` | **PASS** for capture mechanism (Docker Playwright, real page render, ~85KB/frame). **NOT evidence of a live golden campaign** — captured from a run where `campaign.phase=FAILED`, `backend_cost_micros=0`; see correction above. |
| Cost SSE | `cost.snapshot.updated` on campaign path | `apps/api/tests/test_cost_bridge_sse.py` |
| Cost E2E | UI ↔ `GET /v1/ranges/{id}/cost` | **PASS** — `scripts/tactical-cost-e2e-docker.sh` vs prod nip.io |
| Cost restart recovery | Postgres `cost_ledger_campaigns` | `apps/api/ghostrange_api/cost_persistence.py` |
| Reconciliation | `GET .../cost/reconciliation` | `PROVIDER_UNAVAILABLE` until invoice API exists |
| P50/P95 timing | `operation_timing_samples` + `/timing` | Needs ≥5 samples for non-LOW confidence |
| UI/backend cost match | CostIndicator + TaskInspector use API | No client billing formulas |

## Commands

```bash
# Backend
pytest -q packages/cost/tests apps/api/tests/test_cost_bridge_sse.py apps/api/tests/conftest.py

# Live capture (production)
BASE_URL=http://45-76-248-45.nip.io API_URL=http://45-76-248-45.nip.io \
  node scripts/capture-tactical-ui.mjs

# Playwright cost chain (set API to live or local stack)
PLAYWRIGHT_BASE_URL=http://45-76-248-45.nip.io PLAYWRIGHT_API_URL=http://45-76-248-45.nip.io \
  npx playwright test tests/e2e/tactical/tactical-cost.spec.ts --project=chromium

npm run typecheck && npm run test -w apps/web
```

## Human gates (after engineering proof)

- UI-30 — `docs/milestones/M20_UI_ACCEPTANCE_COORDINATION.md`
- TOUR-20 — after timing/cost truth in copy

## Live run (2026-09-27) — corrected

- `artifacts/release-evidence/m20-live-campaign.json` — real HTTP `POST /v1/campaigns/golden` against
  `http://45-76-248-45.nip.io`, `live_mode="live"`, completed in 5.7 seconds (`elapsed_ms: 5747`, not the
  ~4.5 min previously claimed) and returned `"phase": "FAILED"` with `live_worker_outcome: "not_attempted"`
  — a real request against real infra, but a failed campaign, not a completed live run. See correction
  above.
- **Redeploy required** on control VM for: Postgres cost ledger, reconciliation route, timing samples, tactical web bootstrap (this pass’s code).

## Blocked items

| Item | Reason |
|------|--------|
| Provider invoice MATCHED | Vultr API has no campaign-level invoice total |
| GPU telemetry | Phase 8 — not blocking |

## React #185 fix (2026-09-27)

Production blank UI was `Maximum update depth exceeded`: unstable Zustand snapshots in `TourProvider` (`s.steps()` new array every read) and `EventTicker` (`eventLog.slice` in selector). Also `useM20CampaignBootstrap` ignored `VITE_BOOTSTRAP_M20=false` via implicit `PROD && live` enable.
