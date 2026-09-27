# Milestone 2 Coordination — Make One World Real

Scope split (locked by user 2026-09-26): this session (backend) owns Agents 01-11 + 16. Frontend Agents 12/13/14 are owned by the user + a separate peer agent (Cursor) working on `apps/web`. Agent 15 (E2E/browser/perf) is split: mock-provider + API-level E2E is ours; browser/Playwright screenshot capture coordinates with the Cursor peer since it drives `apps/web`.

## Frozen contracts (as of M1 close, 2026-09-26)

`packages/contracts` (ghostrange-contracts) and `packages/events` (ghostrange-events) are real, installed, tested (122/122 passing), JSON-Schema-exported. Treat as FROZEN for M2 wave 1. Any breaking change requires: reason recorded here, migration note, updated tests, and a ping to the Cursor peer since `apps/web` may already consume the exported JSON Schema.

Key modules already implemented — read before writing new code, do not redefine:
- `ghostrange_contracts.range` — RangeSpecV1, RangeV1, RANGE_LIFECYCLE_TRANSITIONS, can_transition/assert_transition
- `ghostrange_contracts.world` — WorldV1, WorldForkV1, NetworkV1/AssetV1/ServiceV1
- `ghostrange_contracts.task` — TaskV1, ResourceProfileV1, RetryPolicyV1, SpeculationPolicyV1
- `ghostrange_contracts.execution_graph` — ExecutionGraphV1, DependencyEdgeV1, ExecutionRecordV1
- `ghostrange_contracts.compute` — ComputeWorkerV1
- `ghostrange_contracts.scheduler` — SchedulerDecisionV1, ReasonCode (10 values)
- `ghostrange_contracts.hypothesis` — HypothesisV1, RemediationV1, AttackAttemptV1
- `ghostrange_contracts.verification` — ObservationV1, VerificationV1
- `ghostrange_contracts.evidence` — ClaimV1, EvidenceV1, ArtifactV1 (content-hash validated)
- `ghostrange_contracts.policy` — PolicyV1, BudgetV1
- `ghostrange_events.*` — 23 events, `EVENT_REGISTRY`, `parse_event()`, `AnyEvent` discriminated union

**Known gap the M2 audit must confirm/size**: these contracts describe `Range`/`World`/`Task` etc. but M2's spec (§11, §12, §13) wants a slightly more granular set for the real pipeline: `ComputeResourceV1` (per-physical-resource tracking, distinct from the logical `ComputeWorkerV1`), and a wider event catalog (`range.requested/validated/authorized`, `execution.requested/authorized/denied/started/completed`, `task.created/cancelled`, richer `world.*`/`compute.*` set). Agent 01 sizes this; likely resolution is ADDITIVE extension of `packages/contracts` and `packages/events`, not a rewrite — confirm before any agent starts removing/renaming existing fields.

## File ownership for M2 wave 1 (disjoint paths — do not edit outside your row)

| Agent | Owns | Must read first |
|---|---|---|
| 01 Audit/Integration | `docs/milestones/M2_AUDIT.md`, this file (updates) | everything — full repo |
| 02 Vultr control-plane | `packages/vultr-control/` | Decisions.md, docs/research/VULTR.md, ADR-006 |
| 03 Range provisioning/IaC | `infra/`, `packages/range-iac/`, `ranges/ghostrange-auth-lab-v1/` | ADR-006, docs/research/VULTR.md (snapshot timing!), packages/contracts/range.py |
| 04 Range runtime | `packages/range-runtime/` | packages/contracts/range.py (RANGE_LIFECYCLE_TRANSITIONS), docs/architecture/PRODUCT.md §3 |
| 05 Security boundary | `docs/security/RANGE_NETWORK_BOUNDARY.md` (new), updates to EXECUTION_POLICY.md/THREAT_MODEL.md | docs/security/*.md (already substantial from M1) |
| 08 Event/persistence | `packages/events/` (additive only), event persistence + SSE/WS layer (new, likely `apps/api/` events module or a small `packages/event-store/`) | packages/events/*, ADR-011-state-sync.md |
| 09 Evidence/verification | `packages/evidence/` | docs/architecture/EVIDENCE.md, packages/contracts/evidence.py + verification.py |
| 10 GhostScheduler v1 | `packages/scheduler/` | docs/research/SCHEDULING.md, SPECULATION.md, ADAPTIVE_COMPUTE.md, packages/contracts/scheduler.py |

Wave 2 (after wave 1 stabilizes): 06 (controlled scenario `ghostrange-auth-lab-v1`), 07 (execution harness — typed actions), 11 (Vultr Serverless Inference planner).
Wave 3: 15 (mock/API E2E — backend half), 16 (failure/cleanup/reconciliation, continuous `docs/milestones/M2_INTEGRATION_STATUS.md`).

## Contract-change protocol
1. Propose the additive field/model in your report, don't just add it silently to a shared file two agents touch.
2. Lead agent (me) reconciles conflicting proposals across agents before merging into packages/contracts.
3. Any RENAME or REMOVAL of an existing V1 field is a breaking change — needs explicit ADR addendum, not a plain edit.

## apps/api
Currently empty. Not explicitly owned by any single M2 wave-1 agent below (M1's backend architect built contracts/events but not the API). Lead agent will assign after Agent 01's audit sizes what's needed for the pipeline in M2 §2 (RangeSpecV1 → validation → policy gate → range-runtime → provider → events).

**2026-09-27 — scope boundary (confirmed with peer session `vultrhack26-27sep-8a`):** `apps/api` now also contains a large pre-existing route surface — `mesh_routes.py`, `causal_routes.py`, `ghostwatch_routes.py`, `ghostgate_bridge.py`, `promotion_routes.py`, `multiverse_fork.py`, `director_routes.py`, `worker_orchestrator.py` — corresponding to M11-M14 (GhostGate/GhostWatch/GhostMesh/GhostCausal per root Progress.md's M1-M14 sweep, recorded there as mock/simulated, NO-GO). This predates or ran alongside this doc's wave-1 effort and is **OUT OF M2 wave-1 SCOPE — do not modify these files.** Agent 08's minimal gateway (WS/SSE replay + golden-path domain-write endpoints per this doc's earlier recommendation) must land as new, additive modules in `apps/api/`, never by editing the files listed above.

## 2026-09-26 — Agent 01 audit addendum (full report: `docs/milestones/M2_AUDIT.md`)

**Confirmed, and sized more precisely than above:**
- `ComputeResourceV1` vs `ComputeWorkerV1` gap is real: `ComputeWorkerV1` today conflates the physical provisioned thing (`provider_instance_id`, `region`, `cost_per_hour_usd`) with the logical scheduling lease (`world_id`, `status`). Recommend additive split (new `ComputeResourceV1` + `ComputeWorkerV1.resource_id` FK) once Agent 02 actually needs multi-worker-per-instance (serverless) — not urgent for wave 1's single-instance-per-worker case, but flagging now so `packages/events`' compute payload classes aren't designed into a corner.
- Event catalog gap is **larger** than `range.*`/`execution.*`/`task.created/cancelled`: of the 21 domain objects in `PRODUCT.md` §2, only 7 (`World`, `Task`, `Agent`, `Evidence`, `Verification`, `ComputeWorker`, `SchedulerDecision`) have any event today. `Range`, `Hypothesis`, `Remediation`, `AttackAttempt`, `Claim`, `Observation`, `ExecutionRecord`, `Policy`, `Budget` have **zero** events. The `execution.requested/authorized/denied/started/completed` gap is the most safety-relevant one — there is currently no event announcing a policy-check ALLOW/DENY decision at all, which matters for anyone building the Evidence UI's "why was this blocked" surface.
- `RemediationV1`/`AttackAttemptV1`/`WorldV1` are each missing fields `PRODUCT.md` specifies (`Remediation.status`/`target_asset_ids`/structured `action_spec`; `AttackAttempt.phase`/`target_asset_ids`; `World.depth`/`compute_worker_ids`/`asset_ids`/`network_ids`/structured `termination_reason`). All additive, not breaking. Full detail in `M2_AUDIT.md` → WHAT IS MISSING.

**New finding, not previously flagged — needs a decision before `apps/api` gateway work starts:**
Three different event-envelope shapes currently exist in committed docs/code and disagree with each other: `packages/events/README.md` (flat payload, no wrapper — the actual implementation), `ADR-011` §3 (generic `{..., type, payload: {...}}` wrapper), and `docs/ui/EVENTS_CONTRACT.md` (a third wrapper shape with an entirely separate event-name vocabulary that has zero overlap with `packages/events`' `EventName` enum). Good news: `apps/web/src/state/eventReducer.ts` has already partially self-resolved this — it has a section explicitly marked `/* —— M2 canonical events (packages/events) —— */` that consumes the real flat `EventName` shape, alongside (not instead of) the legacy wrapper vocabulary for its old M1 demo fixture. **Recommendation: whoever builds `apps/api`'s gateway should follow the flat shape `packages/events`/`apps/web`'s M2 section already agree on, and `ADR-011`/`EVENTS_CONTRACT.md` should get a short amendment pointing at it — not a full rewrite.**

**apps/api ownership recommendation:** none of Agents 02/03/04/05/08/09/10 as currently scoped is a clean fit — 02 (Vultr control-plane), 03 (IaC), 04 (range-runtime), 05 (security docs), 09 (evidence), 10 (scheduler) are all *callees* of the orchestrator `apps/api` is supposed to be per `PRODUCT.md` §4's dependency direction (`apps/web → apps/api → {range-runtime, execution-graph, scheduler, evidence} → {vultr-control, range-iac, adversary-adapter}`). Agent 08 (event/persistence, already scoped to "event persistence + SSE/WS layer... likely `apps/api/` events module") is the closest existing wave-1 assignment — recommend **explicitly widening Agent 08's scope to include a minimal `apps/api`** (the WS/SSE gateway per `ADR-011` §2 + the domain-write endpoints that make `RangeSpecV1 → validation → policy gate → range-runtime → provider → events` actually callable), rather than creating a disjoint new wave-2 role, since the gateway and the event-persistence layer are the same piece of work per `ADR-011`'s own text ("likely `apps/api`, calling into `packages/events`"). If Agent 08's plate is already full once wave 1 lands, the fallback is a new wave-2 assignment scoped narrowly to `apps/api` domain-write endpoints only, with Agent 08 keeping the WS/SSE gateway + `event_log` persistence (since those are one contiguous piece of the state-sync design, not two).

**Process note (not a file-ownership issue, but relevant to "frozen"/"locked" language in this doc):** `git status` currently reports zero commits on `master` — every "frozen" claim above is against uncommitted working tree state, not a commit boundary. Worth an initial commit checkpoint once wave 1 stabilizes, so later contract changes have something concrete to diff against.

**Starting-state snapshot of in-flight packages at time of audit** (expected to be stale immediately — recorded per this doc's instruction to "note what you observed," not as a status report): `packages/evidence` had 3 files (`object_store.py`, `exceptions.py`, `artifact_store.py`, no tests dir yet) and looked complete/careful for what it covered (content-addressed, hash-reverify-on-read). `packages/vultr-control`, `packages/range-iac`, `packages/range-runtime`, `packages/scheduler`, `packages/execution-graph`, `packages/adversary-adapter`, `apps/api`, `infra/`, `ranges/ghostrange-auth-lab-v1/`, `docs/security/RANGE_NETWORK_BOUNDARY.md` were all empty/nonexistent.
