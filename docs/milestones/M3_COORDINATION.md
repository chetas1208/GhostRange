# M3 Coordination — Fork the World (24 agents)

**Lead agent:** integration, contract freeze, conflict resolution, final gate.  
**UI rule:** no fourth tab; no dashboard regression; stable Zustand selectors.

Status: `planned` | `active` | `review` | `done` | `blocked`

## Wave schedule

| Wave | Agents | Gate |
|------|--------|------|
| 0 | 01 | `M3_AUDIT.md` approved |
| 1 | 02, 03, 05, 10, 12, 18, 19 | **Contract freeze** (`multiverse_m3.py` + event names) |
| 2 | 04, 06, 07, 08, 09, 11, 13, 14, 15 | Fork + remediation + verification runtime |
| 3 | 16, 17 | Speculation + adaptive stopping |
| 4 | 20, 21, 22, 23 | Live UI + benchmarks |
| 5 | 24 | Adversarial integration + M3_FINAL |

---

## Agent roster (exactly 24)

| ID | Role | Owns (write) | Consumes | Do-not-touch |
|----|------|--------------|----------|--------------|
| 01 | M3 Audit Lead | `docs/milestones/M3_AUDIT.md` | all | feature code |
| 02 | World Model Architect | `packages/contracts/world.py`, `multiverse_m3.py`, `docs/architecture/WORLD_LINEAGE.md` | M3 audit | apps/web scenes |
| 03 | Forking Researcher | `docs/research/WORLD_FORKING.md`, `docs/adr/ADR-M3-WORLD-FORKING.md` | VULTR.md | vultr-control impl |
| 04 | Vultr Forking Engineer | `packages/vultr-control/`, `packages/range-iac/` fork apply | ADR-M3 | scheduler |
| 05 | Base Immutability Engineer | `packages/range-runtime/` fork capture, fingerprint persist | WorldFingerprintV1 | ui-3d |
| 06 | Remediation Planner | `packages/*/planner` or `apps/api/planner/`, Serverless Inference adapter | RemediationPlanV1 | execution shell |
| 07 | Remediation Actions | `packages/execution-graph/` or `apps/api/remediation/` | policy-check | contracts without 02 |
| 08 | Attack Replay | `AttackReplayPlanV1` impl, auth-lab replay | M2 harness | adversary-adapter (optional) |
| 09 | Regression Suite | `ranges/ghostrange-auth-lab-v1/tests/` | VerificationSuiteV1 | UI |
| 10 | Comparative Verification | `WorldEvaluationV1` pipeline | evidence | scheduler UI |
| 11 | Evidence Isolation | `packages/evidence/` namespaces | provenance | event registry alone |
| 12 | Scheduler Architect | `SchedulingContextV2`, `SchedulerDecisionV2`, `packages/scheduler/v2/` | contracts freeze | vultr-control |
| 13 | Branch Priority | `packages/scheduler/branch_priority.py` | benchmarks | UI |
| 14 | DAG / Critical Path | `packages/execution-graph/` | Task deps | web |
| 15 | Autoscaling | scale-out/in + vultr adapter hooks | ClusterStateV1 | speculation |
| 16 | Speculative Execution | straggler + duplicate tasks | scheduler v2 | UI motion |
| 17 | Adaptive Stopping | EvidenceValueModelV1 (optional exploration) | verification rules | mandatory tests |
| 18 | Budget / Cost | `InvestigationBudgetV1` enforcement | all worlds | UI |
| 19 | Event / Concurrency | `packages/events/` M3 names, idempotency | ADR-011 | reducer (coordinate w/ 20) |
| 20 | Multiverse UI | `apps/web` MultiverseScene, fork layout | real events | Execution/Evidence redesign |
| 21 | Execution UI | Execution scene multi-world + scale | scheduler events | new tabs |
| 22 | Evidence UI | comparative provenance | WorldEvaluationV1 | 3D text |
| 23 | Benchmark / Experiment | `artifacts/benchmarks/m3/`, simulator | scheduler v2 | fake numbers |
| 24 | Red Team / Release | `docs/milestones/M3_FINAL.md`, E2E, failure injection | everything | feature scope creep |

---

## Shared files (lead only unless pinged)

- `packages/contracts/ghostrange_contracts/enums.py` (ReasonCode)
- `packages/events/ghostrange_events/registry.py`
- `apps/web/src/state/eventReducer.ts` (minimal deltas; Agent 19 + 20 pair)
- `docs/milestones/M3_COORDINATION.md`

---

## Contract freeze (Wave 1 complete when exported + tests green)

- `RemediationPlanV1`, `RemediationActionV1`
- `WorldForkV2`, `WorldFingerprintV1`
- `AttackReplayPlanV1`, `VerificationSuiteV1`, `WorldEvaluationV1`
- `SchedulingContextV2`, `SchedulerDecisionV2`
- `InvestigationBudgetV1`

---

## Resource defaults (hackathon-safe)

```yaml
max_worlds: 3
max_cpu_workers: 5
max_gpu_workers: 0
max_runtime_minutes: 45
max_total_cost_usd: configurable
```

---

## Integration checkpoints

After each wave: `npm run typecheck && npm run test && npm run build` + `pytest packages/* apps/api` + mock multi-world E2E (when exists).
