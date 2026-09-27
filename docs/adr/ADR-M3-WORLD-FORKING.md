# ADR-M3: World Forking for Parallel Remediation

**Status:** Accepted (M3 Wave 1)  
**Date:** 2026-09-26  
**Deciders:** Lead agent + Agent 03 (research) + Agent 04 (Vultr)

## Context

M2 proved one disposable world: provision → execute → evidence → teardown. M3 must fork **one base world** into **≥2 real child worlds** with isolated remediation, equivalent verification, scheduler-driven compute, and pruning — without touching production.

GhostRange already has:

- Logical vs physical split (`rangespec.yaml` + `topology.yaml`)
- `WorldForkV1` / `world.forked` event (UI fixture uses this)
- `range-iac` compiler + `MockVultrProvider` / `RealVultrProvider`

## Decision

1. **Fork strategy for M3:** **Template replay (Strategy A)** — each child world is a **new Vultr instance** (or mock instance) created from the same compiled template + cloud-init payload, with child-specific remediation parameters injected at init time. Not snapshot-on-critical-path.

2. **Lineage model:** Persist **`WorldForkV2`** (contracts) linking `base_world_id`, `parent_world_id`, `child_world_id`, `remediation_id`, `fork_point_fingerprint`, `fork_strategy`.

3. **Base immutability:** After fork point, base world is **read-only** for remediation mutations; children carry applied changes. Base may still emit observation events until investigation ends.

4. **Sibling isolation:** Separate provider resource IDs, evidence object key prefixes `{range_id}/{world_id}/`, no shared mutable volumes between children.

5. **Candidate count:** Default **3**, hard cap **5**, enforced by `InvestigationBudgetV1.max_worlds`.

6. **Clusters:** **Defer** Vultr cluster API for M3 default path. Re-evaluate for **worker pool scale-out** (Execution floor) in M3 Wave 2 Agent 15; do not migrate auth-lab logical topology to cluster orchestration in M3.

7. **Serverless Inference:** Plans only — `RemediationPlanV1[]` after schema validation; never direct shell/infrastructure access.

## Consequences

- Fork latency = provision latency × N (bounded N≤3). Acceptable for M3 demo; optimize with golden snapshots in M4.
- `apps/api` orchestrator grows into **investigation coordinator** (fork requests, parallel world state machines).
- UI continues to use **`world.forked`**; payload enriched in events package (Agent 19) to carry `remediation_id`, `generation`, `fork_strategy`.

## Alternatives rejected

- **Snapshot-first fork:** creation time unacceptable on critical path; may add optional fast-path later.
- **Fixture-only forks for M3 done:** rejected — M3 exit requires real child lifecycles (mock provider acceptable if live creds unavailable).

## References

- `docs/research/WORLD_FORKING.md`
- `docs/milestones/M3_AUDIT.md`
