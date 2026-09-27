# Decisions Log (running)

Format: DATE — DECISION — WHY — ALTERNATIVES REJECTED

## 2026-09-26 — Bootstrap decisions (lead agent, pre-research-complete)

These are locked now so 20 parallel workstreams don't diverge. Subagents record deeper justification in ADRs; they may propose changes via ADR addendum, not silent divergence.

1. **Monorepo tool: plain npm workspaces (web) + uv/pip (Python), no Nx/Turborepo yet.**
   Why: two languages, small team, avoid build-tool yak-shaving in M1. Revisit at M2 if build times hurt.

2. **Backend language: Python 3.11+ (FastAPI) for apps/api and all orchestration packages** (range-runtime, scheduler, evidence, vultr-control, adversary-adapter, execution-graph, contracts).
   Why: CALDERA, Atomic Red Team tooling, most cyber-range/agent research code is Python-native. One language for orchestration lowers integration friction with adopted OSS. Go was considered for the control plane (better concurrency primitives) — rejected for M1 because it would split contracts across two type systems with no codegen bridge yet; revisit for range-runtime hot path if Python perf becomes a bottleneck.

3. **Contracts source of truth: Pydantic v2 models in `packages/contracts`, exported to JSON Schema.**
   Why: single authoritative schema, versioned (`RangeSpecV1`, `EvidenceV1`, `SchedulerDecisionV1`). Frontend TS types are hand-written in M1 and checked against exported JSON Schema in CI (no runtime codegen yet — tracked as follow-up, not blocking).

4. **Event transport: Redis/Valkey pub-sub for local + M1 (matches future Vultr-managed Valkey).**
   Why: cheap, already a planned Vultr-native dependency, sufficient ordering guarantees for M1 event volume. Kafka/Argo deferred until multi-worker fan-out actually needs replay/partitioning (ADR-003 documents full reasoning).

5. **Frontend: Vite + React + TypeScript + React Three Fiber + drei (selective) + Zustand for normalized state store.**
   Why: R3F gives idiomatic Three.js in React without a monolithic Scene.tsx; Zustand keeps backend-event-derived state outside Three.js objects per the hard UI rule. No Next.js — no SSR need, avoids extra complexity.

6. **DB: Postgres. Local dev uses containerized Postgres (not SQLite) so schema behavior matches Vultr Managed Postgres from day one.**
   Why: avoid SQLite/Postgres dialect drift discovered late.

7. **IaC: OpenTofu (Terraform-compatible, non-BSL) + cloud-init, targeting Vultr provider.**
   Why: Vultr has a maintained Terraform/OpenTofu provider; instance templates + cloud-init map directly to RangeSpec compilation. Pulumi rejected for M1 — extra language runtime overhead not justified yet.
   **NARROWED 2026-09-26 (Agent 03/range-iac, M2):** for range-ASSET compilation specifically (the actual create-instance/VPC/firewall calls for `ghostrange-auth-lab-v1` and future ranges), `packages/range-iac` compiles directly to `packages/vultr-control` API calls, not generated OpenTofu HCL. Why: ADR-006 already established `packages/vultr-control` as the single choke point for Vultr credentials/safety-boundary enforcement (Decisions.md #9's insertion point); a generated-OpenTofu path would be a second, uncentralized credential path competing with that. OpenTofu remains the right tool for GhostRange's OWN infrastructure (control plane, DB, any non-range-asset infra) — this narrowing applies only to disposable cyber-world assets. See docs/adr/ADR-M2-RANGE-PROVISIONING.md for full reasoning.

8. **Adversary emulation: ADOPT MITRE CALDERA as execution engine dependency, accessed via REST adapter (`packages/adversary-adapter`), not forked/vendored into core.**
   Why: mature ATT&CK-aligned execution + Atomic Red Team integration already solved; reinventing it burns the hackathon clock on a solved problem. GhostRange owns the safety boundary (allowlist, range-ownership token) *around* CALDERA calls, not inside it.

9. **Safety boundary is enforced in `packages/execution-graph` + a policy-check service, not in prompts.**
   Why: explicit requirement — architectural boundary must survive a compromised or adversarial agent, not just a well-behaved one.

## 2026-09-26 — Resolved by research wave 1

10. **Task/hypothesis orchestration engine: ADOPT Ray for `packages/execution-graph`.**
    Why (Agent 04/OSS survey): dynamic task/actor model fits runtime-discovered world-forking better than Argo's static YAML DAGs or Temporal's declared-workflow model; Python-native (matches ADR-002), no k8s dependency, doesn't pre-commit the open VKE-vs-Compute question. Temporal's durable-event-history concept is REFERENCE-only for evidence/audit design, not adopted wholesale. Celery and Argo REJECTed for this purpose.

11. **VKE vs. plain Vultr Compute instances: plain Compute for ALL range assets, always. VKE never used for cyber-world assets** (wrong fidelity primitive — pods aren't believable stand-ins for a domain controller; VMs booted from real images are).
    Why (Agent 05/VULTR.md + ADR-006): resolves prior open question. VKE remains a *possible future* candidate for the orchestration/worker fleet only (Ray workers), never for range assets themselves.

12. **World-fork must use pre-warmed golden snapshots, never snapshot-on-critical-path.**
    Why: Vultr snapshot creation is documented at 20-30 minutes, not instant — a hard constraint on `packages/range-iac` and on any UI claim that forking a world is fast.

13. **GhostScheduler v0 priority formula: reject naive multiplicative form from the original pitch.**
    Why (Agent 10/ADAPTIVE_COMPUTE.md): units mismatch across factors, multiplicative zero-collapse, unbounded blowup as cost→0, no normalization contract, no time/budget coupling.
    Replacement direction: normalize all factors to [0,1] at the contracts schema layer (pydantic field_validator), `value_score = weighted log-sum(evidence_gain, uncertainty_reduction)`, `boost = 1 + weighted_sum(risk, dependency_criticality)` (bounded, floor 1), `priority = value_score * boost / max(cost, cost_floor)`. Full derivation in docs/research/ADAPTIVE_COMPUTE.md — packages/scheduler implementer owns finalizing this.

## 2026-09-26 — Resolved by M2 Agent 09 (Evidence/Verification Engineer)

14. **Evidence artifact storage: content-addressed, keyed by the existing SHA-256 `ArtifactV1.content_hash` — not a hash-chained append-only log.**
    Why: `content_hash` already exists, is already validated at construction (`packages/contracts`), and is already what every other consumer (events, provenance queries, the future Evidence 3D view) keys off of — a hash chain would need a second, parallel identifier nothing else expects. Tamper-evidence is already inherent to content-addressing (bytes that don't hash to their claimed digest are provably invalid on read); a hash chain's extra guarantee — no entry was ever deleted from the sequence — answers a question this product never asks (every real consumer asks "is *this* Artifact still what it claims to be," a per-object question, not a log-integrity one). Dedup is free and materially useful for a scheduler that forks Worlds to compare remediations side by side (recurring boilerplate log/response bytes across Worlds/Executions store once, globally). Maps directly onto Vultr Object Storage's S3-compatible API (docs/research/VULTR.md §7): the content hash *is* the object key.
    Alternatives rejected: append-only hash-chained log per World — rejected because it only strengthens a guarantee ("nothing was ever deleted from this World's evidence sequence") nothing downstream needs, at the cost of a second identifier scheme and losing free cross-World dedup.
    Trade-off accepted: does not by itself prove *when* something was first written, or non-deletion, across the whole store. If that's later needed (e.g. compliance audit trail), the fix is an additive append-only *index* on top (which `packages/evidence`'s `ProvenanceStore` already effectively is), not a replacement of the content-addressed blob layer.
    Implementation: `packages/evidence/ghostrange_evidence/object_store.py` (`LocalFilesystemObjectStore`, `VultrObjectStorageStore`) + `artifact_store.py`. Full reasoning in that module's docstring.

15. **`EvidenceV1.content_hash` stays caller-supplied, not a contract-enforced Merkle root over `observation_ids`/`artifact_ids`.**
    Why: out of scope for `packages/evidence`'s M2 implementation without a contracts change (frozen for wave 1 per M2_COORDINATION.md's contract-change protocol), and no consumer currently needs "the bundle hash changes iff its members change" as an *enforced* invariant rather than a convention — deferring rather than silently deciding a contracts-layer question. Flagged here as still open for whichever agent next touches `packages/contracts/evidence.py`, not closed.

## Open / not yet decided (owned by subagents, see Progress.md)
- Whether `EvidenceV1.content_hash` should be a contract-enforced Merkle root over its members (see #15 above) — still open, owned by whoever next revisits `packages/contracts/evidence.py`.
- Exact stopping-function choice among the three candidates in ADAPTIVE_COMPUTE.md (A: VoI-ratio-with-floor recommended default, B: diminishing-returns slope, C: budget-conditioned dependency veto) — packages/scheduler implementer to finalize, likely A as default with C as an override layer.
