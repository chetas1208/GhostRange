# ghostrange-range-runtime

Owner: Agent 04 (Range Runtime Engineer), Milestone 2.

Drives a `RangeSpecV1` (from `ghostrange_contracts`) through the
authoritative Range lifecycle defined in `ghostrange_contracts.range`
(`RANGE_LIFECYCLE_TRANSITIONS`, `can_transition`, `assert_transition`) —
this package does **not** redefine the state machine, it imports and
enforces it. Every transition is durably persisted and emitted as an
event. See `docs/architecture/PRODUCT.md` §3 for the product-level
lifecycle spec this implements.

## Modules

- `errors.py` — `RangeRuntimeError`, `IllegalTransitionError` (raised for
  any transition not present in `RANGE_LIFECYCLE_TRANSITIONS`),
  `ProviderError`, `ValidationFailedError`.
- `provider.py` — the **port** this package defines for the compute
  provider it drives (`packages/vultr-control`, built concurrently by
  another agent). `ComputeProvider` is a `Protocol`; `FakeComputeProvider`
  is a deterministic, call-counter-driven test double used by every test
  in this package. See "Coordination with vultr-control" below.
- `persistence.py` — durable, append-only transition log plus a snapshot
  table, both SQLite-backed (see "Persistence choice" below).
- `events.py` — event payloads this package emits, and the `EventSink`
  port it publishes them through. Reuses real `ghostrange_events` World
  payloads where they already fit; defines a local, additive
  `RangeTransitionEventV1` for the Range-level transitions that
  `ghostrange_events` does not yet have a home for (see "Event gaps
  found" below — this is a *proposal*, not a silent edit to the frozen
  `packages/events`).
- `engine.py` — `RangeRuntimeEngine`: the actual state machine driver.
- `reconcile.py` — `Reconciler`: DB-truth-vs-provider-truth reconciliation
  loop (see "Reconciliation" below).

## Persistence choice

`Decisions.md` #6 locks Postgres as the project DB, and ADR-011 designs a
Postgres `event_log` table for the *frontend-facing* event replay
pipeline — but that table and its wiring are Agent 08's M2 deliverable
(`packages/events` additive work + event persistence/SSE layer) and did
not exist anywhere in the repo as of this pass (no docker-compose, no
`sqlalchemy`/`psycopg` dependency anywhere in the tree). Standing up a
second, uncoordinated Postgres schema from this package would risk
diverging from whatever Agent 08 lands.

Interim choice for **this package's own** durability requirement ("every
transition must be durable so restarting the process doesn't lose
state"): a well-tested, file-backed **SQLite** append-only log
(`persistence.SqliteTransitionStore`), using only the stdlib `sqlite3`
module (no new dependency). It stores exactly the tuple the brief
specifies — `(range_id, world_id, previous_state, new_state, reason,
correlation_id, timestamp)` — as an append-only `range_transitions`
table, plus a `range_snapshots` table (one row per range, upserted on
every transition) holding the full serialized `RangeV1` so a restarted
process can resume in O(1) instead of replaying the whole log (the log
remains the audit-grade source of truth; the snapshot is a cache derived
from it — `rebuild_range_state()` proves the two agree).

**Migration path**: `SqliteTransitionStore` and any future
`PostgresTransitionStore` should satisfy the same small interface
(`append`, `history`, `latest_state`, `save_snapshot`, `load_snapshot`,
`all_range_ids`) so `RangeRuntimeEngine` doesn't change when the backing
store does. When Agent 08's Postgres `event_log` lands, the natural move
is either (a) point `RangeRuntimeEngine` at a Postgres-backed
implementation of this same interface, or (b) keep this SQLite log as an
internal engine checkpoint and *additionally* publish through whatever
durable sink Agent 08 exposes — not mutually exclusive.

## Coordination with vultr-control

`packages/vultr-control` was empty at the time this package was written
(confirmed via `Progress.md`: "packages/vultr-control code still pending
wave 2" and an empty directory) — Agent 02 is building it concurrently.
Rather than block on it, this package defines the interface it needs as
a `Protocol` (`provider.ComputeProvider`) and drives everything through
that port:

```python
class ComputeProvider(Protocol):
    def start_provisioning(self, *, range_id, world_id, spec, correlation_id) -> None: ...
    def get_state(self, *, range_id, world_id) -> ProviderObservation: ...
    def start_destroy(self, *, range_id, world_id, correlation_id) -> None: ...
```

`get_state` is expected to return one aggregated `ProviderState` for the
whole (range, world) pair — `PROVISIONING`, `BOOTING`, `READY`, `FAILED`,
`DESTROYING`, `DESTROYED`, or `VANISHED` (the resource is gone when the DB
still expects it). Per-asset aggregation (e.g. "BOOTING only once every
asset has left PROVISIONING, READY only once every asset/service is
healthy," mirroring `PRODUCT.md` §3's invariant) is `vultr-control`'s
job, not this package's — this package operates at Range/root-World
granularity only.

**Ask for Agent 02**: when `packages/vultr-control` has real code,
implement `ComputeProvider` (structurally — no import/inheritance
required, it's a `Protocol`) against its real Vultr-backed logic, and
`RangeRuntimeEngine` can be constructed with that implementation instead
of `FakeComputeProvider` with no changes to `engine.py`. If the real
interface needs to be async (`asyncio`, since real Vultr calls are I/O
Vultr HTTP calls) that's a straightforward wrapper adjustment on this
side — flagging this now as a possible future change rather than
guessing at an async signature with nothing on the other side to verify
it against yet.

`FakeComputeProvider` is deterministic and call-counter driven — each
`get_state()` call advances an internal step counter until
`steps_to_ready`/`steps_to_destroyed`, and `inject_failure_at(state)` lets
tests force a `FAILED` observation at a specific stage. It also records
every `start_destroy` call and clears its fake resource list on destroy,
so tests can assert that partial-resource cleanup actually happened on a
failure path, not just that the state flipped to `FAILED`.

## Event gaps found (report, not silently applied)

Per the M2 contract-change protocol in `docs/milestones/M2_COORDINATION.md`
("Propose the additive field/model in your report, don't just add it
silently to a shared file two agents touch"), this pass found three gaps
in the frozen `packages/contracts` / `packages/events`. None of these were
edited — `packages/contracts` and `packages/events` are outside this
package's ownership (M2_COORDINATION.md's file-ownership table: Agent 04
owns `packages/range-runtime` only). Reporting them here + in the
handback report for Agent 01 (audit/integration) and Agent 08
(events/persistence) to size and merge.

1. **VALIDATING / AUTHORIZED are not distinct states in
   `RangeLifecycleState`.** `PRODUCT.md` §3's authoritative transition
   table already conflates them into one `PLANNING` state ("RangeSpec
   resolved, Policy + Budget attached" — both parts happen inside
   `PLANNING`), and `M2_COORDINATION.md` independently flags this exact
   gap as something M2's spec wants split out, likely as an additive
   `range.requested/validated/authorized` event trio. **Confirmed: this
   is a genuine additive gap, not an existing state under a different
   name.** This package does not silently split `PLANNING` in the
   contract. Instead, `RangeRuntimeEngine.validate_and_authorize()`
   performs two real sub-phases while the persisted state stays
   `PLANNING` throughout:
   - a **VALIDATING** sub-phase (spec well-formedness: every asset's
     `network_id` resolves to a declared network, name/owner present) —
     failure here transitions straight to `FAILED` with a reason
     explaining what failed validation (a legal `PLANNING -> FAILED`
     transition, not a bypass of the state machine);
   - an **AUTHORIZED** checkpoint (policy/budget attachment confirmed) —
     recorded as a durable, no-op `PLANNING -> PLANNING` audit row (see
     `persistence.SqliteTransitionStore.append`, which allows
     `previous_state == new_state` for exactly this kind of milestone
     note — it deliberately does **not** go through
     `assert_transition`, since it is not a state change) plus a
     `RangeTransitionEventV1` with matching previous/new state and a
     reason string identifying the sub-phase.
   - **Proposed contract change** (for Agent 01 to size): split
     `RangeLifecycleState.PLANNING` into `VALIDATING` and `AUTHORIZED`
     members, with `RANGE_LIFECYCLE_TRANSITIONS` updated to
     `REQUESTED -> VALIDATING -> AUTHORIZED -> PROVISIONING` (both new
     states also gaining `-> FAILED`). This engine's sub-phase boundary
     already lines up 1:1 with that split, so migrating is a matter of
     changing which `_transition()` calls target which enum member — no
     engine logic needs to be rewritten, only two extra real transitions
     replace one checkpoint-note transition.

2. **`packages/events` has no `range.*` events at all.** Only
   `world.*`, `task.*`, `agent.*`, `evidence.*`, `verification.*`,
   `compute.*`, `scheduler.*` exist in `EventName`/`EVENT_REGISTRY`
   (confirmed by reading `names.py`/`registry.py` directly — every
   `EventName` member was enumerated). `M2_COORDINATION.md` already
   flags this as a known gap for Agent 01's audit. This package emits a
   local, additive `events.RangeTransitionEventV1` for **every** Range
   transition (including the `PLANNING`-internal checkpoint above)
   through an `EventSink` port it owns, deliberately shaped like
   `ghostrange_events._base.GhostRangeEvent` (same envelope fields:
   `event_id`, `occurred_at`, `schema_version`) but *not* registered in
   `EVENT_REGISTRY` — that registration is Agent 08's call, once a real
   `EventName.RANGE_STATE_CHANGED` (or the finer-grained
   `range.requested`/`range.validated`/... trio) is agreed. Moving
   `RangeTransitionEventV1` into `packages/events` verbatim plus adding
   one `EventName` member and one `EVENT_REGISTRY` entry is the expected
   upstream diff.

3. **`WorldStatus` has `EXECUTING`/`VERIFYING`/`FAILED` members with zero
   corresponding events.** `world_events.py` only defines payloads for
   `REQUESTED`/`PROVISIONING`/`READY`/`FORKED`/`DESTROYED` — there is no
   `world.executing`, `world.verifying`, or `world.failed`. Since this
   package treats `packages/range-runtime` as also owning the root
   World's lifecycle (per `PRODUCT.md` §4's package decomposition:
   "Compiles a RangeSpec into a live root World... advances Range/World
   lifecycle state"), it emits real `WorldRequestedV1` /
   `WorldProvisioningV1` / `WorldReadyV1` / `WorldDestroyedV1` for the
   root World at the Range transitions that map cleanly
   (`REQUESTED->PLANNING`, `PLANNING->PROVISIONING`, `BOOTING->READY`,
   `DESTROYING->DESTROYED`), and only the local `RangeTransitionEventV1`
   for the ones that don't have a real payload to reuse
   (`EXECUTING`, `VERIFYING`, `STOPPING`, `FAILED`, `DESTROYING`). Newly
   found gap, not previously flagged anywhere — worth Agent 01/08 sizing
   alongside gap #2.

None of the above blocked implementation; they're additive, and the
engine is written so that adopting the proposed contract/event changes
later is a small, localized diff (see code comments at each call site
tagged `# GAP:`).

## Reconciliation

`reconcile.Reconciler.reconcile_one()` compares this package's own
persisted truth (`SqliteTransitionStore.latest_state`) against
`ComputeProvider.get_state()` for a single Range and drives the
*legal* intermediate transitions to close the gap — it never jumps
straight from `PROVISIONING` to `READY` even if the provider is already
there, it walks `PROVISIONING -> BOOTING -> READY` so every transition is
still recorded and still goes through `assert_transition`. If the
provider reports `VANISHED` (the resource the DB expects is gone) for a
non-terminal Range, it is marked `FAILED` with an explicit reason.
Terminal Ranges (`DESTROYED`/`FAILED`) are always a no-op regardless of
what the provider says — a dead Range does not reanimate.

`reconcile_all()` loops this over every non-terminal range the store
knows about. **What is not wired up yet** (explicitly out of scope for
this package, flagged for the integration owner — Agent 16/01 per
`M2_COORDINATION.md`'s wave plan): a scheduler/cron/background-task
driver that actually *calls* `reconcile_all()` on an interval in a
running process. This package provides the loop; wiring it into
`apps/api` or a standalone worker process is an infra decision belonging
to whoever owns that process's lifecycle.

## Explicitly out of scope for this pass

- Executing `apply_remediation`/`run_attack`/etc. `Task`s — that DAG
  belongs to `packages/execution-graph` per `Decisions.md` #9's safety
  boundary (execution-graph + policy-check, not range-runtime). This
  package only advances `Range`/root-`World` lifecycle state.
- `WorldFork` (non-root World) lifecycle — the task brief and
  `M2_COORDINATION.md`'s ownership row for Agent 04 scope this package
  to `packages/range-runtime` driving the *Range*'s lifecycle (which
  `PRODUCT.md` §4 describes as "compiles a RangeSpec into a live root
  World"). Forked-World lifecycle is a natural extension of the same
  engine shape but is not implemented here to keep this pass's surface
  area reviewable; the `ComputeProvider` port and `SqliteTransitionStore`
  schema both already key on `world_id` generically, so extending
  `RangeRuntimeEngine` (or adding a sibling `WorldForkEngine`) to drive
  non-root Worlds through their own subset of transitions
  (`PROVISIONING -> BOOTING -> READY -> EXECUTING -> VERIFYING -> {...}`
  per `PRODUCT.md` §3) should not require changing this package's
  persistence or provider interfaces.
- Wiring the real Redis/Valkey transport or Postgres `event_log` behind
  `EventSink` — Agent 08's deliverable; this package ships
  `InMemoryEventSink` (tests) and `LoggingEventSink` (a real, if minimal,
  default for a running process) and accepts any object satisfying the
  `EventSink` protocol.

## Running tests

```
cd packages/range-runtime
pip install -e . -e ../contracts -e ../events
pytest
```
