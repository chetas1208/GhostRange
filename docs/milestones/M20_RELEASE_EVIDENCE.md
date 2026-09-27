# M20 release evidence + observability closure

**Scope:** Proof only — no new product subsystems.

## Acceptance checklist

| Gate | Target | Status |
|------|--------|--------|
| Tactical screenshots | 12 / 12 in `artifacts/screenshots/tactical/` | **BLOCKED** on this host (`libasound.so.2`); run on VM or after `playwright install-deps` |
| Cost SSE | `cost.snapshot.updated` on campaign path | `apps/api/tests/test_cost_bridge_sse.py` |
| Cost E2E | UI ↔ `GET /v1/ranges/{id}/cost` | `tests/e2e/tactical/tactical-cost.spec.ts` |
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

## Live run (2026-09-27)

- `artifacts/release-evidence/m20-live-campaign.json` — real `POST /v1/campaigns/golden` against `http://45-76-248-45.nip.io` (~4.5 min).
- **Redeploy required** on control VM for: Postgres cost ledger, reconciliation route, timing samples, tactical web bootstrap (this pass’s code).

## Blocked items

| Item | Reason |
|------|--------|
| 12 PNGs here | Chromium headless needs `libasound.so.2` on capture machine |
| `cost.snapshot.updated` on live until redeploy | Running API predates cost-bridge persistence pass |
| Provider invoice MATCHED | Vultr API has no campaign-level invoice total |
| GPU telemetry | Phase 8 — not blocking |
