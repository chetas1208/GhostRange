# M5 Audit — Wave 0 (2026-09-26)

Lead re-verified repository state before Range Compiler work. Prior milestones remain **partially complete**; M5 builds on existing IaC/compiler foundations, not on a fully live multiverse.

## Verified commands

| Command | Result |
|---------|--------|
| `npm run typecheck` | pass |
| `pytest packages/contracts -q` (isolated) | pass (73) |
| `pytest packages/scheduler -q` (isolated) | pass (119) |
| `scripts/run-mock-m2-e2e.sh` | pass |
| `git log` | **no commits** on `master` |

Note: running `pytest packages/contracts packages/scheduler` together hits a **test module name collision** (`test_scheduler.py`); run packages separately until renamed.

## Milestone honesty

| Milestone | Status |
|-----------|--------|
| M2 one-world API | **MOCK E2E verified**; live Vultr path partial |
| M3 multiverse fork | **NOT COMPLETE** — contracts + UI fixture only |
| M4 GhostScheduler V3 | **Wave 0–1 only** — `plan()` + simulator; benchmarks incomplete |
| Hand-built ranges | **REAL** — `ranges/ghostrange-auth-lab-v1/` (RangeSpec + compose on VM) |

## Component classification (M5 lens)

| Component | Classification | M5 notes |
|-----------|----------------|----------|
| `packages/range-iac` | **IMPLEMENTED_UNVERIFIED** | RangeSpecV1 + topology → Vultr compile; **not** multi-source import |
| `packages/range-iac/loader.py` | **PARTIAL** | Loads checked-in range dirs, not arbitrary Compose/Terraform |
| `packages/vultr-control` | **PARTIAL** | Instance lifecycle; template/snapshot M5 targets |
| `packages/contracts/RangeSpecV1` | **READY_FOR_M5** | Extend with **RangeSpecV2** additive |
| `packages/execution-graph` | **STUB** | Contracts only |
| `packages/adversary-adapter` | **EMPTY** | Verification stays in API/harness for now |
| Compiler from IaC | **BLOCKING_M5** | **M5 primary deliverable** |
| Fidelity engine | **BLOCKING_M5** | Not present pre-M5 |
| UI SourceShadow | **FIXTURE_ONLY** | Multiverse exists; no import pipeline UI |
| Secret safety in import | **BLOCKING_M5** | Mandatory for M5 |

## Existing assets M5 can reuse

- Docker Compose shape in `ranges/ghostrange-auth-lab-v1/docker/vm-1/docker-compose.yml`
- Logical/physical split (`RangeSpecV1` vs `RangeTopologyPlanV1`) per ADR-M2
- Cloud-init embedding path in `range-iac`
- M3 `WorldFingerprintV1` concepts for twin reproducibility

## M5 blockers (priority)

1. **NormalizedSystemGraphV1** + **SourceModelV1** contract freeze  
2. **Real importers** (Compose first, Terraform HCL, K8s YAML) — no regex Terraform  
3. **Sanitization** before any deploy  
4. **FidelityProfileV1 / FidelityReportV1** + gates  
5. **Pipeline** connecting graph → blueprint → placement → RangeSpecV2 → existing `range-iac` compile  
6. **UI** SourceShadow in Multiverse (no new tab)

## Non-goals (M5 prompt)

- Production machine cloning  
- RL scheduler  
- New attack frameworks  
- Fourth primary UI tab  
- Claiming full digital-twin equivalence  
