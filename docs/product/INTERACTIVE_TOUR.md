# GhostRange interactive product tour

**Status:** Engineering **TOUR-READY**; **TOUR-NO-GO** until human TOUR-20 + screenshot capture (`scripts/capture-tour-screenshots.mjs`).

## Entry points

- First-run welcome (`ghostrange.tour.completed` in localStorage)
- HUD **Tour** button (ProductIdentity)
- ⌘K → **Take GhostRange tour** / **Judge tour** / **Restart tour**

## Modes

| Variant | Duration target | Steps |
|---------|-----------------|-------|
| `guided` | ~4–6 min | Full chapter flow |
| `judge` | ~3 min | Subset in `guidedSteps.ts` |
| `technical` | ~8–10 min | Guided + extra control/evolve/arena steps |

## Data

- **Controlled replay** only — HUD shows `◇ CONTROLLED REPLAY`
- Fixture: `demo-auth-incident-031.jsonl` (role-revocation narrative in copy)
- No billable workers on tour start

## Architecture

- `apps/web/src/tour/tourStore.ts` — tour UX state (does not mutate campaign truth)
- `apps/web/src/tour/steps/guidedSteps.ts` — data-driven steps
- `apps/web/src/tour/TourProvider.tsx` — step application + interactions
- DOM: `TourCallout`, `TourProgress`, `TourSpotlight`, `TourWelcome`, `TourSummary`
- 3D: `TourAnchorTracker` + `anchorRegistry`

## E2E

`tests/e2e/tour/tour.spec.ts`

## Screenshots (target)

`artifacts/screenshots/tour/` — capture via Playwright when tour stable
