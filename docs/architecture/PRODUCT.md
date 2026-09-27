# GhostRange — Product Definition & Domain Model

Status: Accepted (M1 baseline). Owner: Agent 01 (Product Architect). Consumers: all other agents — this is the conceptual model `packages/contracts` implements as Pydantic, and the object set every event in `packages/events` describes.

This document is normative. Where it conflicts with informal descriptions elsewhere, this document wins for M1. Proposed changes go through an ADR addendum, not silent divergence (per `Decisions.md`).

---

## 1. Product boundary

### 1.1 What GhostRange IS (falsifiable)

| Claim | How it's falsified if untrue |
|---|---|
| A system that reconstructs authorized infra in disposable, isolated Vultr environments and destroys it when done | Every `Range` reaches a terminal `DESTROYED` state; there is a callable destroy path; no `Range` infra outlives its owning `Range` record without an explicit human-held-open override. |
| A system where remediation candidates compete: each is forked into its own `World`, re-attacked, and independently verified before any verdict is trusted | No `Remediation` can carry status `verified` unless at least one `WorldFork` exists whose child `World` ran a `Verification` referencing that `Remediation` and a suite of `AttackAttempt`s. |
| A system whose scheduling (what runs, where, concurrently with what, for how long, whether to keep spending) is itself a decided, recorded, inspectable thing — GhostScheduler | Every scale-out/in, prune, speculative-branch, or termination action has a corresponding `SchedulerDecision` row with rationale and a cost delta, emitted *before* the action's effects are observable. |
| A system that preserves full provenance from raw forensic bytes to final claims | Every `Claim` has ≥1 supporting `Evidence` id; every `Evidence` row references exactly one content-addressed `Artifact`; nothing here is edited in place, only superseded. |

### 1.2 What GhostRange IS NOT (falsifiable)

| Claim | Enforcement mechanism |
|---|---|
| Not a general-purpose pentesting agent — it will not attack a target outside a `Range`'s own `Policy` allowlist, ever, for any user-supplied target | `packages/execution-graph` + the policy-check service reject any `Task`/`AttackAttempt` whose target `Asset` is not in the active `Policy.asset_allowlist` for that `Range`. There is no override code path that bypasses this from inside an agent's own execution. |
| Not a chatbot around cybersecurity tooling | No product surface is a freeform chat window as its primary interface. The three UI spaces are Multiverse, Execution, Evidence — spatial views of real domain-object state, not a conversation transcript standing in for the product. |
| Not a collection of fake/simulated dashboards | `apps/web` never renders a `Range`/`World`/`ComputeWorker` (or any object below) before the corresponding backend lifecycle event has arrived (see ADR-011). There is no client-side "simulate provisioning" path. Numbers shown (cost, confidence, verification verdicts) are always traceable to a `SchedulerDecision`, `Verification`, or `Budget` row, never hand-authored placeholders. |
| Does not decide what ships to production | A `Verification` verdict is a recommendation backed by evidence; `packages/execution-graph` and `packages/adversary-adapter` have no code path that targets infrastructure outside a `Range`'s own disposable, Vultr-provisioned asset set. Applying a proven `Remediation` to real production is a human action outside GhostRange's execution boundary, full stop. |

---

## 2. Domain model

Conventions:
- Every object has `id` (uuid). Fields below add to that, not repeat it.
- "Belongs to exactly one X" is an invariant, not a suggestion — `packages/contracts` should make the foreign key non-nullable where stated.
- Versioned contract objects (`RangeSpec`, event-carried snapshots) are suffixed `V1` in `packages/contracts` per `Decisions.md` #3; this doc uses the bare name.
- This is the conceptual field list `packages/contracts` translates to Pydantic. It is not itself a schema — types, validation, and JSON Schema export are Backend Architect's (Agent 14) call; semantics are this doc's call.

### 2.1 RangeSpec
The declarative recipe for a `Range`. Immutable once any `Range` references it — content-addressed by hash (`spec_hash`); edits produce a new `RangeSpec`, never a mutation.

- `name`, `description`
- `topology`: declared `Network`s, `Asset`s, `Service`s (templates, not yet materialized instances)
- `incident_scenario_ref`: the seeded vulnerability/incident this spec reproduces (links to research corpus, e.g. a SecRespond-style scenario)
- `default_policy_ref`, `default_budget`
- `provider_profile`: Vultr region/plan mapping defaults
- `created_by`, `created_at`, `spec_hash`, `schema_version`

**Invariant:** a `Range`'s `RangeSpec` reference is fixed at creation; re-running the "same" scenario with changes creates a new `RangeSpec` version, not a patch.

### 2.2 Range
The top-level, addressable "incident universe" — one authorized-infra reconstruction plus everything that happens inside it. Exactly one root `World` belongs to a `Range`; every other `World` in that `Range` descends from the root via zero or more `WorldFork`s.

- `range_spec_id` (+ `spec_hash` snapshot)
- `state` (see §3 — the authoritative Range lifecycle)
- `root_world_id`
- `policy_id` (active `Policy` — see §2.16)
- `budget_id` (top-level `Budget` — see §2.17)
- `provider_context`: Vultr project/region actually used
- `reason`: why this Range exists (free text + `incident_scenario_ref` echo)
- `created_at`, `started_at`, `destroyed_at`

**Invariants:**
- A `Range` has exactly one root `World` (no parent fork).
- A `Range` cannot reach `EXECUTING` before its root `World` reaches `READY`.
- Destroying a `Range` destroys (or has already destroyed) every `World` under it — no orphaned `World` may reference a destroyed `Range`.

### 2.3 World
A specific execution branch/timeline. The root `World` reconstructs the authorized infra as declared by the `RangeSpec`. Every non-root `World` exists to test exactly one `Remediation` candidate against a fresh fork of the environment.

- `range_id`
- `parent_world_id` (**nullable only for the root `World`** of its `Range`)
- `remediation_id` (**nullable only for the root `World`**; set for every forked `World` — the candidate under test)
- `depth`: fork generation counter (root = 0)
- `state` (per-World lifecycle, §3.2)
- `compute_worker_ids`: current `ComputeWorker`s leased to it
- `asset_ids`, `network_ids`: materialized topology instances (each `World`, including forks, has its *own* `Asset`/`Network` instances — never shared across `World`s, even under copy-on-write at the infra layer)
- `created_at`, `terminated_at`, `termination_reason` (`VERIFIED_HOLDS` | `VERIFIED_BROKEN` | `PRUNED_BY_SCHEDULER` | `BUDGET_EXHAUSTED` | `SUPERSEDED` | `FAILED`)

**Invariants:**
- Exactly one `World` per `Range` has `parent_world_id = null` (the root).
- Every non-root `World` has exactly one `WorldFork` record whose `child_world_id` equals its own id (see §2.4) — the fork event and the World's ancestry pointer are kept in sync by construction, not by convention.
- A `World`'s `Asset`s/`Network`s are never referenced by any other `World`.

### 2.4 WorldFork
The discrete *event* of forking — not derivable metadata but its own record, because the Multiverse UI needs a fork to be a thing that *happened* (an event to animate), not just a parent pointer to infer from.

- `range_id`, `parent_world_id`, `child_world_id`
- `remediation_id`: the candidate this fork exists to test
- `forked_by`: `agent_id` or `scheduler_decision_id` that triggered it
- `initial_scheduler_decision_id`: the `SchedulerDecision` that approved committing compute to this fork
- `forked_at`

**Invariant:** `child_world_id` is unique across all `WorldFork` records — a `World` is created by exactly one fork event, ever.

### 2.5 Network
A logical network segment materialized inside one `World`.

- `world_id`, `segment_name`, `cidr`, `security_zone` (`dmz` | `internal` | `management` | ...)

**Invariant:** belongs to exactly one `World`; not shared across forks.

### 2.6 Asset
A concrete host/resource inside a `World`. Maps to a Vultr instance (or other materialized resource) once provisioning completes. **This is the anchor of the safety boundary**: nothing may be targeted by execution unless it is an `Asset` in the allowlist of the owning `Range`'s active `Policy`.

- `world_id`, `network_id`
- `asset_spec_ref`: which declared template in the `RangeSpec` this instantiates
- `role` (`victim-host` | `attacker-host` | `sensor` | `defender-tooling` | ...)
- `vultr_instance_id` (nullable until provisioning completes)
- `state` (mirrors provisioning sub-lifecycle: `PENDING` → `PROVISIONING` → `BOOTING` → `READY` → `DESTROYING` → `DESTROYED` | `FAILED`)
- `allowlisted` (bool; must be `true` for any `Task`/`AttackAttempt` to legally target it — this flag is redundant with `Policy.asset_allowlist` by design: two independent checks, not one)

**Invariant:** `Asset.world_id` must equal the `world_id` of any `Task`/`AttackAttempt` that targets it. Cross-World targeting is not a permissions failure to catch at review time — it must be structurally unrepresentable or rejected at the type/validation layer `packages/execution-graph` sits on.

### 2.7 Service
A logical application/service running on an `Asset` (e.g., "nginx 1.24 w/ seeded misconfig").

- `asset_id`, `service_spec_ref`, `ports`, `version`
- `vulnerability_tags`: refs to seeded CVEs/misconfigs (from the `RangeSpec`'s `incident_scenario_ref`)
- `state` (`installing` | `running` | `crashed` | `patched`)

### 2.8 Agent
An autonomous actor — defender/investigator, adversary, or independent verifier — scoped to a `Range`.

- `range_id` (scope — an `Agent` *record* belongs to one `Range`; the same underlying model/engine config can be reused across `Range`s as separate `Agent` records, not a shared mutable one)
- `role` (`defender` | `adversary` | `verifier` | `scheduler`)
- `engine_ref`: what actually runs it — an LLM model id, or `packages/adversary-adapter`'s CALDERA ability-set reference for adversary agents
- `created_at`

**Invariant:** a `Verification`'s `verifier_agent_id` must differ from the `agent_id` on the `Remediation` it verifies (independence — a proposer cannot grade its own work).

### 2.9 Task
A unit of work by an `Agent` inside a `World`; the node type of `ExecutionGraph`.

- `execution_graph_id`, `world_id`, `agent_id`
- `kind` (`investigate` | `propose_remediation` | `apply_remediation` | `run_attack` | `run_verification` | `collect_evidence`)
- `depends_on`: list of `Task` ids (DAG edges)
- `resource_profile_id`
- `status` (`pending` | `blocked` | `running` | `succeeded` | `failed` | `skipped`)
- `started_at`, `finished_at`, `cost_spent`
- `produced_artifact_ids`

**Invariant:** before dispatch, every `Task` is checked against the owning `Range`'s active `Policy` (target `Asset` allowlist, forbidden techniques, human-approval gates). This check lives in `packages/execution-graph`/policy-check, outside the `Agent`'s own reasoning — it must hold even if the `Agent` is compromised or adversarially prompted.

### 2.10 ExecutionGraph
The DAG of `Task`s for one `World`.

- `world_id`, `root_task_ids`
- `status`: derived (not stored authoritatively) from constituent `Task` states

**Invariant:** exactly one `ExecutionGraph` per `World`. A Range-wide "execution" view (for the Execution UI space) is the union of its Worlds' graphs, not a separate stored object.

### 2.11 ResourceProfile
A named resource *shape request* — decouples what a `Task` needs from what `ComputeWorker` actually serves it. This is the vocabulary GhostScheduler reasons over.

- `cpu`, `memory_gb`, `gpu_type` (nullable)
- `inference_mode` (`serverless` | `dedicated`)
- `vultr_plan_hint`
- `cost_per_hour_estimate`

### 2.12 ComputeWorker
An actual materialized compute unit executing `Task`s — a Vultr instance, or a serverless invocation slot.

- `resource_profile_id`
- `vultr_instance_id` (nullable for serverless)
- `world_id` (current lease — a worker is leased to one `World` while busy; may be reassigned between leases, never shared concurrently across `World`s)
- `state` (`provisioning` | `idle` | `busy` | `draining` | `terminated`)
- `assigned_task_id` (nullable)
- `started_at`, `terminated_at`, `cost_accrued`

**Invariant:** at any instant, a `ComputeWorker`'s cost accrual is attributed to exactly one `World`'s `Budget`. No worker executes `Task`s from two `World`s concurrently.

### 2.13 SchedulerDecision
The audit record of GhostScheduler choosing something. Every scheduler-driven state change must have one of these, emitted before the change's effects are observable — this is what makes GhostScheduler inspectable rather than a black box, and what the Execution UI space renders as the DAG's "why."

- `decision_kind` (`SCALE_OUT` | `SCALE_IN` | `ASSIGN_WORKER` | `BRANCH_PRIORITY` | `PRUNE_BRANCH` | `SPECULATE_BRANCH` | `TERMINATE_INSTANCE` | `ESCALATE_COMPUTE_CLASS` | `DOWNGRADE_COMPUTE_CLASS` | `BLOCK_ON_DEPENDENCY`)
- `subject_type` + `subject_id` (a `Task`, `World`, or `ComputeWorker`)
- `inputs_snapshot`: cost-so-far, verification confidence, budget remaining, straggler signals — whatever fed the decision
- `rationale`: structured + human-readable
- `resulting_action_ref`
- `decided_at`, `decided_by` (scheduler version/build id)

**Invariant:** no component scales, prunes, speculates, or terminates compute without a `SchedulerDecision` record existing first. No silent scheduler action.

### 2.14 Hypothesis
A defender `Agent`'s structured claim about what happened / what's wrong — precursor to a `Remediation`.

- `world_id` (the investigating World, normally the root), `agent_id`
- `statement`: `affected_asset_ids`, `suspected_technique` (ATT&CK id), `confidence`
- `evidence_ids`: supporting evidence
- `status` (`open` | `superseded` | `confirmed` | `rejected`)
- `created_at`

### 2.15 Remediation
A structured, *executable* remediation candidate addressing one `Hypothesis`.

- `hypothesis_id`, `agent_id`
- `description`, `action_spec` (structured — e.g. patch / config-change / firewall-rule; executable by `packages/range-runtime`)
- `target_asset_ids`
- `status` (`proposed` | `forked` | `verified` | `broken` | `rejected` | `superseded`)
- `created_at`

**Invariant:** once a `Remediation` is forked (`WorldFork.remediation_id`), it is applied as exactly one `apply_remediation` `Task` at the start of that child `World`'s execution — never re-applied, never applied to the parent.

### 2.16.a AttackAttempt
A structured adversarial or regression action against a `World` — used both to *reproduce the original incident* (lifecycle step 2) and to *re-test after remediation* (lifecycle step 7). Same object, different `phase`.

- `world_id`, `task_id` (the `Task` that ran it)
- `technique_ref` (ATT&CK id / CALDERA ability id, via `packages/adversary-adapter`)
- `target_asset_ids`
- `phase` (`SEED_INCIDENT` | `REGRESSION_VERIFY` | `ADVERSARIAL_VERIFY`)
- `outcome` (`succeeded` | `blocked` | `detected` | `inconclusive`)
- `evidence_ids`, `executed_at`

### 2.16 Verification
The independent judgment of whether a `Remediation` holds.

- `remediation_id` — **exactly one**
- `suite_run_id` — groups the set of `AttackAttempt`s that constitute **one adversarial/regression suite run**; a `Verification` references exactly one such group, not a loose list re-groupable after the fact. (`suite_run_id` is a lightweight grouping value, not a separate top-level object with its own lifecycle — it exists so this invariant is literally expressible.)
- `world_id`
- `verifier_agent_id` (must differ from the `Remediation`'s `agent_id` — see §2.8)
- `verdict` (`HOLDS` | `BROKEN` | `INCONCLUSIVE`)
- `confidence`, `rationale`, `evidence_ids`
- `verified_at`

**Invariant:** exactly one `Remediation`, exactly one suite run, per `Verification`. A `Remediation` may accumulate multiple `Verification`s over time (e.g. re-verified after a scheduler-triggered re-run), but each is its own complete record — never mutated after `verified_at`.

### 2.17 Evidence
Forensic/observational metadata — the atomic provenance record. Payload lives in `Artifact`; `Evidence` never inlines large bytes.

- `world_id`, `task_id` (nullable if passively collected)
- `kind` (`log` | `network_capture` | `process_snapshot` | `file_diff` | `agent_observation` | `scheduler_decision_ref`)
- `artifact_id`
- `collected_at`, `collected_by` (`agent_id` or `system`)
- `hash`
- `parent_evidence_id` (nullable — for derived evidence, e.g. a parsed summary of a raw capture)

**Invariant:** append-only. Nothing recorded as `Evidence` is ever edited or deleted — only superseded via a new `Claim`.

### 2.18 Artifact
The immutable, content-addressed payload.

- `content_hash` (sha256), `storage_uri`, `mime_type`, `size_bytes`
- `produced_by_task_id`, `created_at`

**Invariant:** immutable once written; identity is its hash, not its id.

### 2.19 Claim
A structured, falsifiable assertion by any `Agent`, always evidence-backed. This is the common node type tying `Hypothesis` and `Verification` verdicts into one provenance graph for the Evidence UI's "constellation."

- `world_id`, `agent_id`
- `claim_type` (`DETECTION` | `ROOT_CAUSE` | `REMEDIATION_EFFECTIVE` | `ATTACK_SUCCEEDED` | ...)
- `statement`
- `supporting_evidence_ids` — **must be non-empty**; a claim with zero evidence is not a `Claim`, it's an unpersisted draft
- `related_hypothesis_id` / `related_verification_id` (at most one set, matching `claim_type`)
- `status` (`asserted` | `retracted` | `superseded`)
- `created_at`

**Invariant:** `supporting_evidence_ids` is never empty for a persisted `Claim`. A `Hypothesis.status = confirmed` or `Verification.verdict` transition SHOULD emit a corresponding `Claim` so the Evidence UI has one consistent assertion type to render regardless of source.

### 2.20 Policy
The declarative safety boundary for a `Range`.

- `range_id`, `version`
- `asset_allowlist` (asset ids or patterns — the authoritative allowlist referenced throughout this doc)
- `forbidden_techniques`
- `requires_human_approval_for`: action types
- `max_budget_id`
- `created_at`

**Invariant:** every `Task` and `AttackAttempt` is checked against the `Range`'s *active* `Policy` before execution, unconditionally. (Detailed enforcement design is Agent 13's — `docs/security/THREAT_MODEL.md`/`EXECUTION_POLICY.md` — this doc fixes that the check must exist and what it's checked against.)

### 2.21 Budget
Cost/resource ceiling tracking, nested: one per `Range` (ceiling), one per `World` (allocation carved from the `Range`'s remaining balance).

- `kind` (`RANGE` | `WORLD`), `range_id` or `world_id`
- `currency_units` (abstract compute-dollars), `allocated`, `spent`, `remaining`
- `exhausted_at` (nullable)

**Invariant:** a `World`'s `Budget.allocated` must not exceed its parent `Range` `Budget`'s `remaining` at fork time. `SCALE_IN`/`PRUNE_BRANCH` `SchedulerDecision`s are the real-time mechanism keeping this true as spend accrues.

---

## 3. Range & World lifecycle — reconciled state machine

Two state-machine sketches exist in the source spec:

- **Fine-grained:** `REQUESTED → PLANNING → PROVISIONING → BOOTING → READY → EXECUTING → VERIFYING → STOPPING → DESTROYING → DESTROYED`, with `FAILED` reachable from any non-terminal state.
- **Coarse:** `CREATE → BOOT → READY → RUNNING → VERIFYING → DESTROYING → DESTROYED`.

**Resolution: the fine-grained machine is authoritative for the persisted `Range.state` field and for events.** The coarse machine is a *derived display projection* — useful for a compact UI affordance or a status-line summary — never a second source of truth. Mapping:

| Coarse (display projection) | Fine-grained (authoritative, persisted) |
|---|---|
| `CREATE` | `REQUESTED`, `PLANNING` |
| `BOOT` | `PROVISIONING`, `BOOTING` |
| `READY` | `READY` |
| `RUNNING` | `EXECUTING` |
| `VERIFYING` | `VERIFYING` |
| `DESTROYING` | `STOPPING`, `DESTROYING` |
| `DESTROYED` | `DESTROYED` |
| *(any)* | `FAILED` — terminal, reachable from any non-terminal state in both views; the coarse view just shows `FAILED` directly with no analogue collapse needed |

Transition rules on the authoritative machine:

```
REQUESTED    -> PLANNING       (RangeSpec resolved, Policy + Budget attached)
PLANNING     -> PROVISIONING   (IaC plan compiled by range-iac, Vultr calls begin)
PROVISIONING -> BOOTING        (Vultr instances materialized, cloud-init running)
BOOTING      -> READY          (all root-World Assets/Services report healthy)
READY        -> EXECUTING      (first Task dispatched against the root World)
EXECUTING    -> VERIFYING      (a Verification is requested for ≥1 forked World)
VERIFYING    -> EXECUTING      (allowed: verification failure spawns further remediation work)
VERIFYING    -> STOPPING       (all open Remediation candidates verified or abandoned, or Budget exhausted)
EXECUTING    -> STOPPING       (Budget exhausted or human-initiated stop, verification never reached)
STOPPING     -> DESTROYING     (evidence/artifact export confirmed complete, or explicit override)
DESTROYING   -> DESTROYED      (all Assets/ComputeWorkers under the Range confirmed torn down)
*            -> FAILED         (terminal; from any non-terminal state)
```

`World.state` mirrors a subset of this per-`World` (a fork skips `REQUESTED`/`PLANNING` — it inherits its spec context from the parent at fork time — and adds terminal states specific to verification outcome):

```
(created by WorldFork, already PLANNING-equivalent)
PROVISIONING -> BOOTING -> READY -> EXECUTING -> VERIFYING
VERIFYING -> { VERIFIED_HOLDS | VERIFIED_BROKEN | PRUNED_BY_SCHEDULER } -> DESTROYING -> DESTROYED
* -> FAILED
```

**Invariant:** a `Range` cannot leave `PLANNING` until its root `World` is instantiated; the root `World` cannot leave `READY` until every `Asset` it owns reports `READY`. `STOPPING`→`DESTROYING` must not proceed while any `Evidence`/`Artifact` write for that `Range` is still in flight (see PRODUCT invariant §4.8).

---

## 4. System decomposition

```
apps/api                 FastAPI orchestrator. Hosts the domain services that own writes
                          to Range/World/Task/etc., runs Policy checks at dispatch time
                          (in concert with execution-graph), and is the sole event producer
                          boundary for external consumers (owns the WS/SSE gateway — see
                          ADR-011). Owner: Agent 14.

packages/contracts        Pydantic v2 models — the implementation of §2 of this doc.
                          Exports JSON Schema; versioned (RangeSpecV1, EvidenceV1,
                          SchedulerDecisionV1, ...). Owner: Agent 14.

packages/events            Event envelope definitions + pub/sub client wrapper (Redis/
                          Valkey) + the durable event_log contract used for replay
                          (see ADR-011). Consumed by every producer package and by
                          apps/api's gateway. Owner: Agent 15.

packages/range-runtime      Compiles a RangeSpec into a live root World: drives
                          range-iac + vultr-control to materialize Networks/Assets/
                          Services, executes apply_remediation Tasks, advances
                          Range/World lifecycle state. Owner: Agent 07.

packages/execution-graph     The Task DAG engine AND the safety boundary: policy-check
                          enforcement lives here (per Decisions.md #9) — no Task or
                          AttackAttempt dispatches without an allowlist check against
                          the owning Range's active Policy. Owner: Agent 11 (DAG) +
                          Agent 13 (policy semantics, docs/security/).

packages/scheduler          GhostScheduler: consumes ExecutionGraph state, ResourceProfile
                          requests, Budget remaining, straggler/verification signals;
                          emits SchedulerDecision records; is the only legitimate source
                          of SCALE_*/PRUNE_*/TERMINATE_* actions. Owner: Agent 08-10
                          (research) inform Agent scheduler implementation (unassigned
                          in Batch D per Progress.md — flagged, see §6).

packages/evidence           Evidence/Artifact/Claim storage, provenance chain, content
                          addressing. Owner: Agent 12.

packages/adversary-adapter    CALDERA REST client; translates AttackAttempt requests to
                          CALDERA operations/abilities and normalizes results back into
                          the AttackAttempt shape. GhostRange's safety boundary wraps
                          this package, not the inverse. Owner: Agent 04.

packages/vultr-control       Vultr API wrapper: instance/network lifecycle for both
                          Range infra (Assets) and ComputeWorkers. Owner: Agent 05.

packages/range-iac          OpenTofu module generation + cloud-init templating from
                          RangeSpec/Asset declarations. Owner: Agent 06.

packages/ui-3d               Shared Three.js/R3F primitives used by all three apps/web
                          spaces. Owner: Agent 16 (architecture) / Agents 17-19 (usage).

apps/web                   Multiverse / Execution / Evidence spaces. Consumes ONLY
                          packages/events + packages/contracts types + the apps/api
                          gateway — never talks to Postgres or Vultr directly. See
                          ADR-011 for the state-sync contract this depends on.
```

Dependency direction (informal): `apps/web` → `packages/events` + `packages/contracts` (read-only) → `apps/api` (the only writer) → {`range-runtime`, `execution-graph`, `scheduler`, `evidence`} → {`vultr-control`, `range-iac`, `adversary-adapter`}. No package below `apps/api` in this chain should import anything from `apps/web`.

---

## 5. Architectural invariants

These must always hold. Each is meant to be checkable in code review or a test, not aspirational prose.

1. **No execution outside the allowlist.** No `Task` or `AttackAttempt` may target an `Asset` not in the owning `Range`'s active `Policy.asset_allowlist`. Enforced in `packages/execution-graph`, independent of any `Agent`'s own behavior — must survive a compromised or adversarially-prompted agent.
2. **Events precede UI state, always.** Every state transition of every object in §2 is emitted as an event via `packages/events` before (or atomically with) the persisted change becoming visible to `apps/web`. The frontend store never fabricates, predicts, or optimistically renders domain-object state ahead of a received event (see ADR-011).
3. **Exactly one fork edge.** A `World` has exactly one `WorldFork` record pointing to it, except the `Range`'s root `World`, which has none.
4. **Verification independence.** A `Verification`'s `verifier_agent_id` differs from the `Remediation`'s proposing `agent_id`; a `Verification` references exactly one `Remediation` and exactly one suite run.
5. **Immutable specs.** `RangeSpec` and `Remediation.action_spec` are immutable once referenced by a `Range`/`WorldFork` — content-addressed; changes create new versions, never in-place mutation.
6. **Append-only provenance.** `Evidence` and `Artifact` records are never edited or deleted; superseding happens via a new `Claim`, not a rewrite.
7. **Budget attribution is exclusive and real-time.** A `ComputeWorker`'s cost accrual is attributed to exactly one `World`'s `Budget` at any instant; a `World`'s allocation never exceeds its parent `Range`'s remaining balance at fork time.
8. **Safe destruction.** `STOPPING → DESTROYING` does not proceed while any `Evidence`/`Artifact` write for that `Range` is still in flight, absent an explicit human override.
9. **Production is out of scope, structurally.** There is no code path in `packages/execution-graph` or `packages/adversary-adapter` that can target infrastructure outside a `Range`'s own Vultr-provisioned, disposable asset set. Applying a proven `Remediation` to real production is a human action taken outside GhostRange.
10. **No silent scheduling.** No component scales, prunes, speculates on, or terminates compute without a corresponding `SchedulerDecision` record existing first.

---

## 6. Open items / flags for the lead agent

- **GhostScheduler implementation ownership** (`packages/scheduler` code, not just research) is not clearly assigned an implementer in `Progress.md`'s Batch D row — Agents 08-10 are research-only. Recommend Batch D pick this up explicitly before Wave 2 closes, since `execution-graph` and `evidence` both take scheduler-shaped inputs (`SchedulerDecision`) as a dependency.
- **Policy enforcement split**: this doc assumes a single logical "policy-check" enforcement point inside `packages/execution-graph`, per `Decisions.md` #9. Agent 13's `EXECUTION_POLICY.md` should confirm whether that's literally one function/module or a dedicated internal service — either is consistent with this doc, but the two shouldn't diverge on where the allowlist check physically lives.
- **`suite_run_id`** (§2.16) is introduced here as a lightweight grouping value, not a new top-level stored entity, specifically to satisfy the spec's "one Verification references... one suite run" requirement without adding a 22nd domain object. Backend Architect: treat it as a field/foreign key on `AttackAttempt` and `Verification`, not a new table with its own lifecycle, unless a concrete need emerges.
