# M3 Audit — Wave 0 (2026-09-26)

Lead agent re-verified M2 before M3 fork work. Method: read source + run tests (not summaries).

## M2 subsystem classification (M3 lens)

| Subsystem | M3 classification | Notes |
|-----------|-------------------|--------|
| apps/web UI | **READY_FOR_M3** | Fork visuals exist on **fixture**; must bind to real `world.forked` + lifecycle; **React #185 fixed — do not break selectors** |
| packages/ui-3d | **READY_FOR_M3** | WorldFork, WorldCollapse, ProvisioningGhost, etc. |
| packages/contracts | **READY_FOR_M3** | `WorldForkV1`, `RemediationV1` exist; **M3 additive models** in `multiverse_m3.py` |
| packages/events | **READY_FOR_M3** | `world.forked` payload exists; needs M3 event expansion (Wave 1 Agent 19) |
| packages/range-runtime | **REAL_PARTIAL** | Single-world lifecycle strong; **no fork runtime** |
| packages/range-iac | **REAL_PARTIAL** | Compiler supports fork mode concept (ADR-M2); **not wired to multi-world orchestrator** |
| packages/vultr-control | **REAL_PARTIAL** | Create/destroy/wait; **no fork-specific clone path verified live** |
| packages/scheduler | **READY_FOR_M3** | V1 task placement; needs **V2 branch-aware** (Agent 12–17) |
| packages/evidence | **REAL_PARTIAL** | Deterministic auth-lab verification; **no per-world namespace enforcement in API** |
| packages/policy-check | **READY_FOR_M3** | Authorize path exists; must gate remediation actions |
| packages/execution-graph | **INCOMPLETE** | Contracts only — **BLOCKING_M3** for typed DAG across worlds |
| packages/adversary-adapter | **EMPTY** | Attack replay may start in `apps/api` harness (Agent 08) |
| apps/api | **MOCK_ONLY** | Single-world M2 orchestrator; **BLOCKING_M3** for fork orchestration |
| Postgres EventGateway | **INCOMPLETE** | Implemented in events store; not default in API |
| Real Vultr multi-world | **FIXTURE_ONLY** | No live 3-world run yet |
| Git baseline | **BLOCKING_M3** | Still **zero commits** — establish before large M3 diffs |

## Verified commands (this audit)

- `npm run typecheck` — pass  
- `npm run test` (web) — 7/7 pass  
- `scripts/run-mock-m2-e2e.sh` — pass  
- `pytest packages/contracts` — pass after M3 contract tests added  

## M3 blockers (priority)

1. **Fork runtime** — persist lineage, provision N child worlds, isolate budgets/evidence.  
2. **Orchestrator** — extend `apps/api` (or `range-runtime`) for base → 3 candidates → parallel verification → prune.  
3. **GhostScheduler V2** — branch priority, scale, prune decisions with new reason codes.  
4. **Comparable verification** — `VerificationSuiteV1` + `AttackReplayPlanV1` enforced per world.  
5. **UI integration** — real events only; no new primary tabs; stable Zustand selectors.

## Non-goals for M3 (explicit)

- RL / neural scheduler  
- Unlimited recursive branching depth  
- GPU by default ( **`GPU_NOT_JUSTIFIED`** is a success case)  
- Replacing spatial UI with dashboards  

## Docs missing from prompt paths (use equivalents)

| Prompt path | Actual |
|-------------|--------|
| docs/PRODUCT.md | `docs/architecture/PRODUCT.md` |
| docs/ARCHITECTURE.md | ADRs + `THREE_D_ARCHITECTURE.md` |
| docs/ROADMAP.md | `Progress.md` |
| docs/DECISIONS.md | `Decisions.md` |
| M2_INTEGRATION_STATUS.md | `M2_COMPLETION_AUDIT.md` + `M2_FINAL.md` |
