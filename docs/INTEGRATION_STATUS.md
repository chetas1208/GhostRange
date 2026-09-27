# Integration status (living)

Last updated: 2026-09-26

## End-to-end paths

| Path | Status | Command / endpoint |
|------|--------|-------------------|
| Mock M2 one-world | **PASS** | `POST /v1/ranges/{id}/runs/m2` |
| M10 golden path (mock) | **PASS** | `POST /v1/golden-path/runs` + SSE events |
| M3 multiverse fork (mock events) | **PASS** | `POST /v1/ranges/{id}/forks/multiverse` |
| Scheduler V3 preview | **PASS** | `POST /v1/scheduler/plan-preview` |
| Live Vultr golden | **NOT RUN** | `GHOSTRANGE_LIVE=true` + lease |
| UI LIVE mode | **READY** | `VITE_DATA_SOURCE=live` + `VITE_RANGE_ID` |

## Package matrix

| Package | Tests | Wired to API |
|---------|-------|--------------|
| contracts | yes | yes |
| events | yes | memory gateway |
| range-compiler | yes | golden path |
| scheduler V3 | yes | scheduler routes + golden path |
| ghostdirector | yes | golden path |
| adversarial-verifier | yes | golden path |
| ghostledger | yes | golden path |
| execution-graph | yes | standalone |
| adversary-adapter | yes | standalone (Caldera safety) |
| range-runtime | yes | M2 orchestrator |

## Known gaps

- Postgres default for API events (still memory gateway)
- Multi-world fork not tied to real provider provisioning
- No git baseline commit yet (user decision)
