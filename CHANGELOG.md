# Changelog

## 0.1.0 (unreleased)

### Added

- **M20** `GhostCampaignV1`, report/bundle/reproduction contracts; `POST /v1/campaigns/golden`; `scripts/m20-release-check.sh`, `scripts/m20-golden-path.sh`
- M19 GhostArena package + GhostEvolve production promotion gate
- M10 mock golden path orchestrator and `POST /v1/golden-path/runs` with SSE phase events
- GhostScheduler `POST /v1/scheduler/plan-preview`
- M3 mock multiverse fork endpoint
- Packages: `ghostrange-execution-graph`, `ghostrange-adversary-adapter` (Caldera safety boundary)
- Makefile targets: `test`, `demo`, `golden-path`
- Execution UI: Director vs Scheduler strip (live event log)
- `.env.example`, `docs/OPERATIONS.md`, `docs/INTEGRATION_STATUS.md`

### Fixed

- Renamed `packages/contracts/tests/test_scheduler.py` → `test_scheduler_v1_contracts.py` (pytest collision)
- `AuthAdminLabScenario.execute()` for adversarial engine protocol

### Known limitations

- Live Vultr golden path not executed without credentials
- M9/M8/M7 full gates not closed; integration-focused M10 in progress
