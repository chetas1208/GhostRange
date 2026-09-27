# M10 Audit — Wave 0 (2026-09-26)

**Verified against repository state; M9_FINAL and prior milestone docs are not trusted without tests.**

## Git / release hygiene

| Item | Classification |
|------|----------------|
| Commits on `master` | **NONE** (entire tree untracked) |
| `Progress.md` | **CONTRACT_DRIFT** vs packages M3–M9 |
| Milestone `M*_FINAL.md` | M2 partial; M3–M6 stubs; M7–M9 **in progress** honestly marked |

## M9 GhostDirector (verified)

| Item | Classification |
|------|----------------|
| `ghostdirector_m9.py` contracts | **REAL_VERIFIED** |
| `GhostDirectorSimulator` + 7 tests | **REAL_COMPONENT_ONLY** |
| API / SSE / UI integration | **NOT DONE** |
| Live campaign on Vultr | **NOT DONE** |
| GhostLedger director provenance | **NOT DONE** |

**M9 completion gate (prompt §145): NOT MET.** M10 proceeds as **integration campaign**, not assuming M9 closed.

## Cross-milestone capability (summary)

| Subsystem | Classification |
|-----------|----------------|
| Range compiler (compose/tf) | **REAL_COMPONENT_ONLY** (9 tests) |
| Fidelity / drift (M6) | **REAL_COMPONENT_ONLY** (unit tests) |
| GhostScheduler V3 | **REAL_COMPONENT_ONLY** (119 tests) |
| M2 API one-world orchestrator | **MOCK_ONLY** E2E (FakeCompute / MockVultr) |
| World forking (M3) | **PARTIAL / CONTRACT** |
| GhostLedger seal/verify | **REAL_COMPONENT_ONLY** (8 tests) |
| Adversarial verifier | **REAL_COMPONENT_ONLY** (8 tests) |
| 3D UI (Multiverse/Execution/Evidence) | **FIXTURE_ONLY** primary path |
| Live Vultr golden path | **BLOCKING_RELEASE** until credentials + lease |

## Test matrix (2026-09-26 spot run)

| Suite | Result |
|-------|--------|
| contracts (subset) + ghostledger + scheduler + range-compiler + adversarial + ghostdirector | **155 passed** |
| `apps/api` mock M2 E2E | **pass** (when run via script) |
| Full monorepo `pytest packages/contracts` | **may fail** on duplicate `test_scheduler` collection at package root |
| Browser E2E / chaos / live Vultr | **not re-run in this audit** |

## BLOCKING_M10 (release)

- No single orchestrated golden path through API (until M10 Wave 1+)
- Director/Scheduler/Adversarial/Ledger not one pipeline
- UI not driven by golden-path backend events
- No confirmed live teardown + orphan scan
- No Agent 40 GO

## READY_FOR_M10

- All major packages importable
- Mock M2 pipeline + SSE proven
- Director/adversarial/ledger simulators testable in-process
- Auth-lab range + compiler fixture path exists

## Duplication / drift notes

- Two hypothesis models: `HypothesisV1` (incident) vs `InvestigationHypothesisV1` (M9) — **intentional**, document in canonical contracts
- Scheduler: V1 decisions in M2 API vs V3 in packages — **adapter needed** for golden path
- `packages/director/` path in prompt → actual package **`packages/ghostdirector`**
