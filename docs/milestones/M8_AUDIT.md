# M8 Audit — Wave 0 (2026-09-26)

Audit before Adversarial Verification Engine implementation.

## Git / process

| Item | Classification |
|------|----------------|
| Commits on `master` | **NONE** (entire tree untracked) |
| `Progress.md` | **STALE** vs packages |

## M7 GhostLedger (independently verified)

| Item | Classification |
|------|----------------|
| `ExperimentManifestV1` + contracts | **REAL_VERIFIED** (schema tests) |
| `seal_experiment` / `verify_bundle` | **REAL_VERIFIED** (8 pytest) |
| Golden bundles | **FIXTURE_ONLY** (`valid-full`, `tampered-manifest`) |
| Offline CLI `ghostrange-verify` | **IMPLEMENTED_UNVERIFIED** (manual smoke) |
| Runtime capture from API | **NOT DONE** |
| Live replay / Vultr bundle demo | **NOT DONE** |
| Sigstore / Rekor | **NOT DONE** |
| Full tamper matrix | **PARTIAL** |

## M6 Living Twin

| Item | Classification |
|------|----------------|
| Drift engine + unit tests | **REAL_VERIFIED** |
| Claim validity STALE | **PARTIAL** (planner, no API persistence) |

## M5 / M4 / M3 / M2

| Item | Classification |
|------|----------------|
| Range compiler (compose/tf/k8s) | **REAL_VERIFIED** (9 tests) |
| GhostScheduler V3 plan | **REAL_VERIFIED** (119 tests) |
| Multiverse fork runtime | **PARTIAL / MOCK** |
| API orchestrator | **MOCK_ONLY** (one-world) |
| Auth lab range | **REAL** (docker, placeholder apps) |

## Evidence / claims

| Item | Classification |
|------|----------------|
| `ClaimV1` | **REAL** (no adversarial lifecycle fields yet) |
| `AssumptionV1` (M6) | **CONTRACT** |
| Attack replay / verification suite (M3) | **CONTRACT** |

## Quality matrix (2026-09-26)

| Check | Result |
|-------|--------|
| `pytest packages/ghostledger/tests` | 8 pass |
| `pytest packages/scheduler/tests` | 119 pass |
| `pytest packages/range-compiler/tests` | 9 pass |
| `pytest packages/contracts/tests` | **BLOCKED** if repo root collects duplicate `test_scheduler` — run `packages/contracts/tests/` explicitly or fix collision |
| Browser E2E / full monorepo lint | not re-run this audit |

## READY_FOR_M8

- Typed claims + assumptions contracts  
- Scheduler V3 for compute allocation patterns  
- GhostLedger experiment sealing (for search provenance hooks)  
- Auth-lab HTTP chain for controlled in-process scenarios  
- Event package extensibility  

## BLOCKING_M8 (full gate)

- No persisted claim adversarial state in API/DB  
- No live disposable Vultr search worlds wired  
- M7 replay not production-ready  
- UI still fixture-driven for multiverse search  

## M8 starting point

Build **claim-bounded falsification** in-process first (`packages/adversarial-verifier`), benchmark with hidden ground truth separated from search code, then wire API/events/UI.
