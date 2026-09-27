# M9 Audit — Wave 0 (2026-09-26)

Independent verification before GhostDirector work.

## Git

| Item | Status |
|------|--------|
| Commits | **NONE** (untracked tree) |

## M8 Adversarial Verifier (verified)

| Item | Classification |
|------|----------------|
| `adversarial_m8.py` contracts | **REAL_VERIFIED** |
| `run_adversarial_search` + auth-lab scenario | **REAL_VERIFIED** (8 pytest) |
| Safety oracle / minimize / confirm | **REAL_VERIFIED** |
| API / UI / Vultr live search | **NOT DONE** |
| GhostLedger search provenance | **NOT DONE** |

## M7 GhostLedger

| Item | Classification |
|------|----------------|
| Seal + offline verify | **REAL_VERIFIED** (8 pytest) |
| Runtime API capture | **PARTIAL / NOT DONE** |

## GhostScheduler (M4)

| Item | Classification |
|------|----------------|
| V3 `plan()` | **REAL_VERIFIED** (119 tests) |
| Search arm allocation (M8 policies) | **SEPARATE** from task scheduling — **REAL** in adversarial package |

## Separation check (M9 prerequisite)

| System | Question | Status |
|--------|----------|--------|
| GhostScheduler | HOW to run approved work? | **Exists** |
| GhostDirector | WHAT experiment next? | **NOT BUILT** (M9) |
| Merged into one planner? | Must be **NO** | OK today |

## Knowledge / hypotheses today

| Item | Classification |
|------|----------------|
| `HypothesisV1` (incident/remediation) | **REAL** — different domain from M9 investigation hypotheses |
| `AssumptionV1` (M6) | **CONTRACT** |
| `ClaimV1` | **REAL** — no director lifecycle |

## READY_FOR_M9

- M8 `RUN_COUNTEREXAMPLE_SEARCH` as future **ExperimentOperator**
- M4 cost models in scheduler config
- M6 drift → uncertainty source
- Adversarial + ledger contracts for provenance extension
- In-process benchmark worlds (auth-lab pattern)

## BLOCKING_M9 (full gate)

- No `InvestigationKnowledgeStateV1` persisted
- No API campaign endpoints
- No UI Director/Scheduler layers
- No Vultr live campaign
- GhostLedger director decisions not sealed

## Quality matrix (spot check)

| Suite | Result |
|-------|--------|
| adversarial + ghostledger + scheduler | **135 passed** |

Full monorepo lint/E2E not re-run this audit.
