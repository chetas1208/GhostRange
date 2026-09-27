# M2 Audit — GhostRange, run by Agent 01 (Auditor/Integration Architect)

Audited 2026-09-26. This is a point-in-time snapshot; several packages (`packages/vultr-control`,
`packages/range-iac`, `packages/range-runtime`, `packages/evidence`, `packages/scheduler`,
`docs/security/RANGE_NETWORK_BOUNDARY.md`, `packages/events` additive work) are being actively
written by other agents in parallel and will have moved on from what's described here. `apps/web`
is owned by the Cursor peer and is noted for existence/build status only — not audited for
internal defects.

Method: every claim below was checked by reading the actual source (not just docs) and by
actually running the available build/test commands. Commands + real output are quoted where
it matters.

---

## WHAT EXISTS

Repo root: `Decisions.md`, `Progress.md`, `README.md`, `package.json` (npm workspaces:
`apps/web`, `packages/ui-3d`), a `.venv` (Python 3.13, `ghostrange-contracts` and
`ghostrange-events` installed editable), `.hacp/` (HACP peer-coordination log/lock/session),
`artifacts/{benchmarks,screenshots}/m2` (empty leaf dirs, no content yet), `ranges/`,
`scripts/` (`capture-m2-screenshots-docker.sh`, `capture-ui-snapshots.mjs`), `tests/` (empty),
`infra/` (empty).

- `packages/contracts` — real. 15 modules (`range.py`, `world.py`, `asset.py`, `agent.py`,
  `task.py`, `execution_graph.py`, `scheduler.py`, `hypothesis.py`, `verification.py`,
  `evidence.py`, `policy.py`, `compute.py`, `enums.py`, `_base.py`, `export_schema.py`), 8 test
  files, 28 exported JSON Schemas under `schemas/`.
- `packages/events` — real. `EventName` enum (23 members), one Pydantic payload class per
  name across 7 modules, `registry.py` (`EVENT_REGISTRY`, `AnyEvent`, `parse_event`), 2 test
  files. **No Redis/Valkey client code and no Postgres `event_log` code exist** despite
  `PRODUCT.md` §4 describing `packages/events` as owning "pub/sub client wrapper... + the
  durable event_log contract" — only the schema/registry half is built.
  `packages/events/README.md` states the shape explicitly: "one flat payload per event, not an
  envelope wrapper" — no generic `Envelope[Payload]`.
- `packages/evidence` — in progress (Agent 09, live under this audit). At time of reading:
  `object_store.py`, `exceptions.py`, `artifact_store.py`. No `pyproject.toml` test wiring
  observed yet, no tests directory. `ArtifactStore` is a real, careful implementation
  (content-addressed, re-verifies hash on read, raises `ArtifactTamperedError` on mismatch).
- `packages/vultr-control`, `packages/range-iac`, `packages/range-runtime`,
  `packages/scheduler`, `packages/execution-graph`, `packages/adversary-adapter`, `apps/api`,
  `infra/`, `ranges/ghostrange-auth-lab-v1/`, `tests/`, `docs/integrations/` — **empty
  directories, zero files**, at time of this audit.
- `apps/web` — real, substantial, and actively growing under this audit (new files appeared
  between the first and second directory scan performed in this session — Cursor peer is live).
  Includes a full R3F app shell, DOM HUD layer, inspectors, canvas/scene composition, a
  normalized Zustand store + event reducer, two JSONL demo fixtures, and its own UI
  specification docs (`docs/ui/UI_SPECIFICATION.md`, `EVENTS_CONTRACT.md`, `LIVE_STATE_MAPPING.md`,
  `INTERACTION_MODEL.md`, `THREE_D_ARCHITECTURE.md`).
- `packages/ui-3d` — real, 30 `.tsx`/`.ts` components across agents/canvas/compute/evidence/
  network/scheduler/temporal/world subfolders.
- `docs/` — architecture (`PRODUCT.md`, 4 ADRs, `EVIDENCE.md`), research (7 files), security
  (`THREAT_MODEL.md` 203 lines, `EXECUTION_POLICY.md` 425 lines), ui (5 files + snapshots dir,
  currently empty), milestones (`M2_COORDINATION.md`, this file).
- **Version control note:** `git status` reports `fatal: your current branch 'master' does not
  have any commits yet` — every file in this repo, including M1's "locked" contracts and
  "frozen" events package, is currently uncommitted working tree state. There is no commit to
  roll back to and no history to diff against. Flagging this because M2_COORDINATION.md's
  "frozen" language implies a committed baseline that does not actually exist yet.

---

## WHAT WORKS (real command output)

**`packages/contracts` tests:**
```
$ cd packages/contracts && python3 -m pytest -q
.................................................                        [100%]
49 passed in 0.20s
```

**`packages/events` tests:**
```
$ cd packages/events && python3 -m pytest -q
........................................................................ [ 98%]
.                                                                        [100%]
73 passed in 0.19s
```
Total: **122/122 passing**, confirming Progress.md's claim exactly.

**Editable installs resolve correctly:**
```
$ pip show ghostrange-contracts ghostrange-events
Editable project location: .../packages/contracts   (Requires: pydantic)
Editable project location: .../packages/events      (Requires: ghostrange-contracts, pydantic)
```

**Schema export is reproducible and matches what's committed:** regenerating all 28 schemas to
a scratch dir and diffing against `packages/contracts/schemas/` produced zero differences —
the committed JSON Schemas are not stale relative to the Pydantic source.

**`apps/web` builds:**
```
$ npm run build --workspace=apps/web
✓ 1183 modules transformed.
dist/assets/index-Be1nfm9n.js   1,234.98 kB │ gzip: 346.25 kB
✓ built in 5.62s
```
(One non-fatal warning: main JS chunk >500kB, no code-splitting yet — cosmetic, not a build
failure.)

**Typecheck passes for both TS workspaces:**
```
$ npm run typecheck
> tsc --noEmit   (packages/ui-3d)   → no output, exit clean
> tsc --noEmit   (apps/web)         → no output, exit clean
```

**`ArtifactStore.get_bytes` re-verifies hash on every read** (read the code directly, not just
the docstring) — this is a real tamper-evidence check, not an aspiration.

---

## WHAT IS MOCKED

- Nothing in the backend currently makes any Vultr API call, mocked or real —
  `packages/vultr-control` is an empty directory. There is no mock provider yet to audit.
- `apps/web`'s two JSONL fixtures (`demo-auth-incident-031.jsonl`, `m2-auth-lab-v1.jsonl`) are
  honestly labeled as fixtures (HUD shows amber `FIXTURE` per `LIVE_STATE_MAPPING.md`) and are
  clearly separated from a "LIVE"/"LIVE (offline)" data source path in
  `apps/web/src/hooks/useRangeDataSource.ts` and friends — this is the right shape for "no fake
  provider success," it's just that there is no real backend yet for LIVE mode to actually
  connect to (`apps/api` doesn't exist).
- `ComputeProvider.LOCAL_MOCK` exists as an enum value in `packages/contracts` and is used by
  the `m2-auth-lab-v1.jsonl` fixture (`"provider":"LOCAL_MOCK"`), i.e. the *concept* of a
  labeled mock provider is already in the contract layer, waiting for `range-runtime`/
  `vultr-control` to implement it.

---

## WHAT IS PARTIAL

- **`packages/events`**: schema/registry half only. No transport (Redis/Valkey publish/
  subscribe wrapper) and no durable `event_log` persistence, both of which `PRODUCT.md` §4 and
  `ADR-011` assign to this package/`apps/api`.
- **`packages/evidence`**: `ArtifactStore`/`ObjectStore`/exceptions exist and look solid; no
  `ClaimV1`/`EvidenceV1`/`ObservationV1` persistence layer observed yet, no tests directory yet
  (in-flight, expected to change).
- **Event coverage vs. the domain model**: of the 21 domain objects in `PRODUCT.md` §2, only
  `World`, `Task`, `Agent`, `Evidence`, `Verification`, `ComputeWorker`, and `SchedulerDecision`
  have any corresponding events. `Range`, `WorldFork` (partially — `world.forked` exists but no
  independent `Range`-level event), `Hypothesis`, `Remediation`, `AttackAttempt`, `Claim`,
  `Observation`, `ExecutionRecord`, `Policy`, and `Budget` have **zero** events, despite
  `PRODUCT.md` architectural invariant #2 ("every state transition of every object in §2 is
  emitted as an event... before... becoming visible to `apps/web`"). See MISSING below for the
  itemized list.
- **`RangeLifecycleState`** in `packages/contracts/enums.py` has 11 states matching PRODUCT.md's
  authoritative machine (`REQUESTED, PLANNING, PROVISIONING, BOOTING, READY, EXECUTING,
  VERIFYING, STOPPING, DESTROYING, DESTROYED, FAILED`) — but the M2 spec's stated lifecycle
  (`REQUESTED→VALIDATING→AUTHORIZED→PROVISIONING→...`) wants an explicit two-step gate
  (schema/policy *validation*, then a distinct *authorization* decision) where the current model
  has one state, `PLANNING`, covering both. Functionally the transition table still allows
  `REQUESTED→PLANNING→PROVISIONING`, so this is a granularity gap, not a broken state machine —
  but there is currently no way to observe "spec is valid but not yet authorized" as a distinct,
  eventable state, which matters for a system whose whole safety story is an explicit
  authorization gate before any Vultr spend happens.

---

## WHAT IS BROKEN

Nothing that currently exists is broken by its own tests/build. Every package that has code
(`packages/contracts`, `packages/events`, `apps/web`, `packages/ui-3d`) passes its own test/
build/typecheck suite with real, reproduced output (above). No broken code was found — the
gaps below are absence of code, not failing code.

One process-level issue: the repo has **zero git commits** (see WHAT EXISTS) — this isn't
"broken" software, but it means "frozen"/"locked" claims in `Decisions.md` and
`M2_COORDINATION.md` have no actual commit boundary backing them yet, which matters once
multiple agents are editing disjoint paths concurrently and something needs to be diffed or
reverted.

---

## WHAT IS MISSING

**Confirmed and sized, the gap `M2_COORDINATION.md` flagged, plus others found:**

1. **`ComputeResourceV1` vs `ComputeWorkerV1` — confirmed gap, more specific than flagged.**
   `ComputeWorkerV1` (`packages/contracts/compute.py`) already conflates the *logical*
   scheduling unit (`world_id` lease, `assigned_task_id`-equivalent, `status`) with the
   *physical* provisioned thing (`provider_instance_id`, `region`, `cost_per_hour_usd`). For
   M2's real pipeline (one Vultr instance may eventually host more than one worker slot, e.g.
   under serverless inference — see `docs/research/ADAPTIVE_COMPUTE.md`/`VULTR.md`), these need
   to be splittable: a `ComputeResourceV1` (the physical Vultr instance/resource, 1:1 with
   `provider_instance_id`) that one or more logical `ComputeWorkerV1` records reference. **This
   should be an additive split** (new `ComputeResourceV1` model + `ComputeWorkerV1.resource_id`
   FK), not a rename, since `ComputeWorkerV1` is already event-carrying (`compute.ready`
   payload class references its fields directly) and 4+ event payload classes assume today's
   flat shape.

2. **Event catalog — the real gap is larger than "range.*/execution.*/task.created/cancelled."**
   Confirmed missing exactly as flagged, plus:
   - `range.*` events: **zero** exist. `Range` is the top-level object per `PRODUCT.md` §2.2 and
     has its own 11-state lifecycle distinct from `World`'s — nothing announces any Range
     transition today, not even `range.requested`.
   - `execution.*` events (`requested/authorized/denied/started/completed`): **zero** exist.
     This is the most safety-relevant gap — `docs/security/EXECUTION_POLICY.md` describes a
     policy-check service that issues ALLOW/DENY decisions before any Task/AttackAttempt
     executes, but there is no event announcing that decision, which means today's evidence/UI
     surface has no way to show *why* something was allowed or blocked at dispatch time (as
     opposed to `scheduler.decision`, which is a different kind of decision).
   - `task.created` / `task.cancelled`: `TaskStatus` enum already has `CANCELLED` as a value,
     but no `TASK_CANCELLED` event exists, and the current first task event is `task.queued`
     (there's no `task.created` distinct from "queued for scheduling").
   - Also missing entirely, not previously flagged: any event for `Hypothesis`, `Remediation`,
     `AttackAttempt`, `Claim`, `Observation`, `ExecutionRecord`, `Policy`, or `Budget` — i.e. the
     entire investigate → remediate → attack → claim chain that is the actual product thesis
     (`PRODUCT.md` §1.1's second falsifiable claim) currently has no event trail at all except
     the single generic `evidence.created`.

3. **`apps/api` — entirely unbuilt**, confirmed empty, and is the single largest concrete
   blocker to "one real RangeSpec provisioned through Vultr" per the M2 mandate, since
   `ADR-011`'s whole state-sync design (WS gateway, replay-then-live-tail, Postgres `event_log`)
   depends on it and nothing else in the repo currently owns writes to any domain object.

4. **`RemediationV1` and `AttackAttemptV1` are missing PRODUCT.md-specified fields**, not just
   events: `RemediationV1` has no `status` field at all (PRODUCT.md §2.15 wants
   `proposed|forked|verified|broken|rejected|superseded`) and no `target_asset_ids`; its
   `actions: list[str]` is unstructured free text where PRODUCT.md wants a structured,
   range-runtime-executable `action_spec`. `AttackAttemptV1` has no `phase` field
   (`SEED_INCIDENT|REGRESSION_VERIFY|ADVERSARIAL_VERIFY`) and no `target_asset_ids`, both
   required by PRODUCT.md §2.16.a for the same object to serve both the "reproduce the incident"
   and "re-test after remediation" roles the product thesis depends on.

5. **`WorldV1` is missing fork/termination detail PRODUCT.md specifies**: no `depth` (fork
   generation counter), no `compute_worker_ids`/`asset_ids`/`network_ids`, and
   `termination_reason` is a free-text `failure_reason: Optional[str]` rather than the
   structured enum PRODUCT.md §2.3 specifies
   (`VERIFIED_HOLDS|VERIFIED_BROKEN|PRUNED_BY_SCHEDULER|BUDGET_EXHAUSTED|SUPERSEDED|FAILED`).

6. **No safety-boundary code exists yet to check against.** `docs/security/EXECUTION_POLICY.md`
   describes a standalone policy-check service in detail (down to token/ticket signing), but
   `packages/execution-graph` (where `Decisions.md` #9 says enforcement lives) is an empty
   directory. Nothing currently enforces `PRODUCT.md` invariant #1 ("no execution outside the
   allowlist") in code — it exists only as design.

7. **`ranges/ghostrange-auth-lab-v1/` is empty.** M2 wave 2 (Agent 06) is scoped to build this
   controlled scenario; confirmed nothing exists there yet, consistent with it being a
   wave-2 (not wave-1) assignment.

---

## WHAT CONTRADICTS M1 DOCUMENTATION

1. **Three different, mutually inconsistent event-envelope shapes exist simultaneously in
   committed docs/code, and none of them has "won" yet:**
   - `packages/events/README.md` (Agent 15, the actual implementation): explicitly **"one flat
     payload per event, not an envelope wrapper"** — `event_id`/`event_name`/`occurred_at`/
     `schema_version` sit flat alongside the event's own fields in one JSON object.
   - `docs/architecture/ADR-011-state-sync.md` §3 (Agent 01, this session's own prior M1 output):
     specifies a **generic wrapper envelope** — `{event_id, range_id, world_id, seq, type,
     schema_version, occurred_at, payload: {...}}` — with `type` values like `"world.forked"`
     and payload nested under `payload`.
   - `docs/ui/EVENTS_CONTRACT.md` (Cursor peer, M1): a **third** envelope shape —
     `{id, sequence, type, occurred_at, payload}` (no `range_id`/`world_id`/`schema_version` at
     the envelope level) — with its own event-type vocabulary (`range.updated`, `world.created`,
     `world.status_changed`, `asset.upserted`, `link.upserted`, `attack.observed`,
     `compute.worker_upserted`, etc.) that has **no overlap at all** with `packages/events`'
     `EventName` enum.
   These three documents cannot all be implemented as written — whichever wins, this needs an
   explicit reconciliation before `apps/api`'s gateway is built, or `apps/api` will end up
   guessing which of its own M1-era design docs to follow.

2. **`apps/web`'s actual reducer code has already partially reconciled this itself**, ahead of
   any doc update: `apps/web/src/state/eventReducer.ts` has a section explicitly commented
   `/* —— M2 canonical events (packages/events) —— */` that switches on the real 23
   `EventName` values (`world.requested`, `compute.ready`, `task.queued`, etc.) using the flat
   (non-wrapper) shape, alongside — not instead of — the older EVENTS_CONTRACT.md vocabulary for
   its legacy M1 demo fixture. `apps/web/src/state/normalizeEnvelope.ts` also already accepts
   both `raw.event_name` (backend flat shape) and `raw.type` (wrapper shape) opportunistically.
   **This is good news, not a defect** — the frontend is more current than the M1 docs are — but
   it means `ADR-011` and `EVENTS_CONTRACT.md` are now *stale relative to the code that's
   supposed to implement them*, and whoever builds `apps/api` should follow the flat shape
   `packages/events` and `apps/web`'s M2 section already agree on, not ADR-011's wrapper.

3. **`PRODUCT.md` §4 describes `packages/events` as owning "pub/sub client wrapper (Redis/
   Valkey) + the durable event_log contract used for replay,"** but no such code exists in
   `packages/events` — only Pydantic schemas/registry. This isn't a contradiction of fact so
   much as a description of unbuilt scope; flagged here because a new agent picking up
   `packages/events` "additive only" work (per `M2_COORDINATION.md`'s file-ownership table)
   could reasonably read `PRODUCT.md` §4 and start building transport code inside
   `packages/events`, when `ADR-011`'s own "Negative / accepted debt" section says this logic
   "likely" belongs in `apps/api` calling into `packages/events`. Worth an explicit decision
   before wave 2, not a silent pick.

4. **`RangeV1` (runtime record) doesn't carry `policy_id`/`budget_id`/`provider_context`/`reason`**
   that `PRODUCT.md` §2.2 specifies for it directly — only `RangeSpecV1` (the declarative input)
   has `policy_id`/`budget_id`. This may be an intentional simplification (Range inherits its
   spec's policy/budget by reference) but as written it's a silent narrowing versus the
   normative doc, not a documented one.

---

## WHAT SHOULD BE PRESERVED

- `packages/contracts` and `packages/events` as they stand: 122/122 real tests, schemas
  regenerate identically to what's committed, clean typed models with real validators
  (SHA-256 format checks, self-loop rejection on DAG edges, `RANGE_LIFECYCLE_TRANSITIONS` as an
  explicit table with `assert_transition`). This is genuinely load-bearing, well-tested code —
  additive extension is the right call, not a rewrite, matching what `M2_COORDINATION.md`
  already concluded.
- `packages/evidence`'s `ArtifactStore` design (content-addressing, re-verify-on-read, explicit
  `ArtifactTamperedError`) — keep this pattern as the model for how the rest of the evidence
  chain (`ClaimV1`/`ObservationV1` persistence) should be built.
- `apps/web`'s discipline about not inventing state ahead of events (`normalizeEnvelope`,
  the FIXTURE/LIVE/LIVE-offline HUD distinction, `no solid ComputeNode before compute.ready`) —
  this is the one hard product rule and the frontend is actually honoring it structurally, not
  just in a comment.
- The `docs/security/EXECUTION_POLICY.md` design (standalone policy-check service, ticket-based
  defense in depth) — it's detailed and considered; nothing in this audit found a reason to
  redesign it, only to note it isn't implemented yet.

## WHAT SHOULD BE REFACTORED

- The event-envelope question (contradiction #1 above) needs one explicit decision recorded in
  `Decisions.md`, then `ADR-011` and `docs/ui/EVENTS_CONTRACT.md` need a short amendment (not a
  rewrite) pointing at the flat shape `packages/events`/`apps/web`'s M2 section already use.
  This is process/doc refactoring, not code refactoring — no working code needs to change.
- `ComputeWorkerV1` → additive split into `ComputeResourceV1` (physical) +
  `ComputeWorkerV1.resource_id` (logical, FK) once Agent 02/vultr-control's design needs it —
  don't do this preemptively before that package has an actual multi-worker-per-instance use
  case to justify it, but flag it now so the event payload classes referencing
  `ComputeWorkerV1` fields directly (`compute.ready`, etc.) are designed with the future split
  in mind rather than needing a breaking change later.
- `RemediationV1`/`AttackAttemptV1` should gain the missing fields (`status`,
  `target_asset_ids`, `phase`) additively before `packages/execution-graph` or
  `packages/scheduler` start depending on their current (incomplete) shape — cheaper to add now
  than to migrate consumers later.

## WHAT SHOULD NOT BE TOUCHED YET

- `packages/vultr-control`, `packages/range-iac`, `packages/range-runtime`,
  `docs/security/RANGE_NETWORK_BOUNDARY.md`, `packages/evidence`, `packages/scheduler` — all
  actively owned and in-progress by other M2 wave-1 agents per `M2_COORDINATION.md`; this audit
  only read their current state, made no edits.
- `apps/web`, `packages/ui-3d`, and all `docs/ui/*.md` — Cursor peer's territory per the M2
  scope split; noted for existence/build status only (both build/typecheck cleanly as of this
  audit), not audited for internal defects, per this task's explicit instruction.
- `packages/contracts`/`packages/events` frozen fields — do not rename or remove anything;
  every gap identified above is additive (new fields, new models, new events), consistent with
  `M2_COORDINATION.md`'s contract-change protocol.
