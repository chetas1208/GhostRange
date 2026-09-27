# M2 Final Report — GhostRange (in progress)

**Campaign:** ONE WORLD REAL (backend). **UI:** complete enough — not reworked.

## WHAT IS REAL?

- **GhostScheduler v1** — deterministic decisions with `ReasonCode`s (115 scheduler tests).
- **Range runtime state machine** — illegal transitions fail; SQLite persistence (153 tests).
- **Vultr control plane code** — `RealVultrProvider` + mock/fake HTTP tests (91 tests).
- **Range IaC compiler** — single-VM auth-lab topology + cloud-init (24 tests).
- **Evidence** — content-addressed artifacts + rule-based auth-lab verification (32 tests).
- **Policy-check** — execution authorization service (40 tests).
- **Live API (mock path)** — `POST /v1/ranges/{id}/runs/m2` drives provisioning → execution → evidence → verification → teardown events; **SSE + snapshot** match `apps/web` `normalizeEnvelope` / `eventReducer`.

## WHAT REMAINS MOCKED?

- Default API run uses **`MockVultrProvider`** via `VultrAdaptedComputeProvider` (`GHOSTRANGE_LIVE_PROVIDER=mock`).
- HTTP validation uses **simulated** 401 response unless a real `base_url` is configured.
- Event transport default is **in-memory** (not Postgres/Redis) for CI mock E2E.

## DID A REAL VULTR RESOURCE GET CREATED?

**No** in this environment. `LIVE_PROVIDER_TEST=NOT_RUN_NO_CREDENTIALS` unless `VULTR_API_KEY` is set and `GHOSTRANGE_LIVE_PROVIDER=vultr`.

## UI LIVE CONSUMPTION

Set:

```bash
# apps/web/.env.local
VITE_DATA_SOURCE=live
VITE_API_BASE=http://127.0.0.1:8000
VITE_RANGE_ID=<uuid-from-post-runs-m2>
```

Start API: `ghostrange-api` (from `apps/api`). HUD should show **LIVE** when SSE connects.

## TESTS

- Frontend: typecheck + 7 tests + build — **pass**
- Backend: **637** Python tests + **1** mock M2 API E2E — **pass** (with venv installs)

## REMAINS FOR M3

- Real multi-world forks on Vultr (not fixture-only branches). **→ M3 campaign started:** see `docs/milestones/M3_AUDIT.md`, `M3_COORDINATION.md`, `ADR-M3-WORLD-FORKING.md`.
- Serverless inference plan generation (bounded, schema-validated).
- Full execution-graph + Caldera adapter.
- Postgres-backed authoritative event log in production API path.
