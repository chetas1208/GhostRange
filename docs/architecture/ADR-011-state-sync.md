# ADR-011: State Synchronization (Backend → Frontend)

- **Status:** Accepted
- **Date:** 2026-09-26
- **Owner:** Agent 01 (Product Architect)
- **Relationship to other decisions:** builds on `Decisions.md` #4 (Redis/Valkey pub-sub for M1, Kafka deferred to ADR-003) and #5 (Zustand normalized store). Consumed by `packages/events` (Agent 15, implementation), `apps/api` (Agent 14, gateway), and Batch E (Agents 16-19, frontend consumption). This ADR is new design, not a formalization of an already-locked choice — it resolves an open question the product spec states as a hard constraint but doesn't mechanize.

## Context

The product's UI hard rule (stated directly in the spec): *"A machine provisioning on Vultr must only materialize in the UI after the corresponding backend lifecycle event arrives — never invented."* This generalizes to every domain object in `docs/architecture/PRODUCT.md` §2 — `Range`, `World`, `WorldFork`, `Asset`, `ComputeWorker`, `SchedulerDecision`, `Verification`, `Evidence`, `Claim`, `Budget`, etc. Three spatial UI spaces (Multiverse, Execution, Evidence) all render live derivations of this same backend state, and per `PRODUCT.md` architectural invariant #2, none of them may fabricate, predict, or optimistically render state ahead of a real backend event.

Constraints already locked that this design must work within:
- Event transport is Redis/Valkey pub-sub for M1 (`Decisions.md` #4) — chosen for cost and because it's a planned Vultr-native dependency, but it has **no built-in durability or replay**: a subscriber that's offline or reconnecting misses whatever was published while it was away. Kafka (which would solve this natively) is explicitly deferred until multi-worker fan-out needs replay/partitioning that pub-sub can't provide (ADR-003, not yet written).
- Frontend state lives in a normalized Zustand store (`Decisions.md` #5), kept deliberately outside Three.js scene objects.
- DB is Postgres (`Decisions.md` #6), already the source of truth for persisted domain objects.

The open problem this ADR solves: given a non-durable pub/sub transport, how does a frontend client that just loaded (or just reconnected after a network blip) get a *correct* current state, and then stay correct, without ever inventing something the backend hasn't confirmed?

## Decision

**One-way, event-sourced-at-the-edge synchronization**: backend domain services emit events for every state transition; those events are both published live (Redis/Valkey) and durably appended (Postgres); a single per-`Range` gateway endpoint in `apps/api` serves both catch-up replay and live tail through the same contract; the frontend's only path to mutating its store is applying received events.

### 1. Event production

Every state transition of every object in `PRODUCT.md` §2 is emitted as a typed, versioned event by whichever package owns that transition (`apps/api` domain services, `packages/range-runtime`, `packages/scheduler`, `packages/evidence`, `packages/execution-graph`). Producers call `packages/events`, which does two things on every publish, in this order:

1. **Append** the event to a durable Postgres table, `event_log`:
   - `event_id` (uuid, primary key)
   - `range_id` (partition key for ordering — see below)
   - `seq` (integer, monotonically increasing **per `range_id`**, assigned at append time — e.g. via a Postgres sequence or `SELECT ... FOR UPDATE` on a per-range counter row)
   - `type` (e.g. `"range.state_changed"`, `"world.forked"`, `"task.status_changed"`, `"scheduler.decision_recorded"`, `"evidence.collected"`, `"verification.recorded"`)
   - `payload` (JSON — the relevant `packages/contracts` model, serialized)
   - `schema_version`
   - `occurred_at`
2. **Publish** the same event to the Redis/Valkey channel for that `range_id` (e.g. channel `range.{range_id}.events`).

The append happens first and is the operation that assigns `seq`; the publish is best-effort live delivery. This ordering means the durable log is always at least as current as anything a live subscriber could have seen — a client can never observe a live event whose `seq` isn't already durably recorded.

### 2. The gateway contract (`apps/api`)

`apps/api` exposes one WebSocket endpoint per `Range`: `WS /ranges/{range_id}/events?since_seq={n}`.

On connect:
1. Server queries `event_log` for all rows with that `range_id` and `seq > since_seq` (or `since_seq` omitted/0 → full history, which for a freshly-created `Range` is just its creation event; the API may also offer a cheaper "current snapshot" bootstrap for very old Ranges — out of scope for M1 given Range lifetimes are short-lived by design).
2. Server streams those rows in `seq` order as the replay batch.
3. Server then subscribes the connection to the live Redis/Valkey channel for that `range_id` and forwards subsequent messages as they arrive.
4. If a live message arrives with `seq <= last replayed seq` (a race between step 1's query and the subscribe in step 3), it's dropped — the replay already covered it. This makes the handover between replay and live tail safe without needing a distributed lock.

This is the *only* way `apps/web` learns about backend state. There is no separate REST "get current state" endpoint that a UI component polls directly for domain-object state — a fresh page load is just `since_seq=0` on this same endpoint.

### 3. Event envelope (frontend-facing shape)

```
{
  event_id: string (uuid)
  range_id: string
  world_id: string | null
  seq: number            // monotonic per range_id
  type: string            // e.g. "world.forked"
  schema_version: number
  occurred_at: string     // ISO 8601
  payload: {...}          // shape matches the packages/contracts model for `type`
}
```

`type` values are namespaced `<entity>.<transition>` and payloads mirror the relevant model in `PRODUCT.md` §2 as exported by `packages/contracts`' JSON Schema — this is the concrete point where `Decisions.md` #3's "frontend TS types checked against exported JSON Schema in CI" bites: the frontend's hand-written event payload types are checked against schemas generated from the same Pydantic models the backend actually serializes.

### 4. Frontend ingestion (the only store-mutation path)

A single ingestion module owns all writes to the Zustand store:

- On receiving an event, it looks up the entity by `(type's entity, id-field-in-payload)`, and applies the payload as that entity's current state in the store, keyed by entity id.
- It tracks `last_applied_seq` per `range_id`. Events are applied in `seq` order; an event with `seq <= last_applied_seq` for its range is a duplicate (can legitimately happen across reconnects) and is dropped, not reapplied.
- An event with `seq` that skips ahead unexpectedly (gap) triggers a reconnect-and-replay from `last_applied_seq` — the client never tries to "fill the gap" by guessing.
- **No other code path writes domain-entity state into this store.** UI interaction handlers (e.g., a "propose this remediation" button) call `apps/api` REST endpoints, which validate, persist, and emit the resulting event(s) through the pipeline above. The UI does not locally construct the new `Remediation`/`WorldFork`/etc. and render it before the event round-trips back — this is the literal mechanism satisfying the product's "never invented" rule.
- All three UI spaces (Multiverse, Execution, Evidence) read from this same normalized store. None maintains its own copy of entity state, so the three spatial views cannot drift relative to each other or to the backend.

### 5. Ordering & idempotency guarantees this gives

- **Per-range total order**: `seq` is monotonic per `range_id`, assigned at durable-append time, so replay + live-tail handover (step 2.4 above) can never apply events out of order or skip one.
- **Idempotent apply**: applying the same event twice (possible across a reconnect boundary) is a no-op because of the `seq` check — producers do not need to guarantee exactly-once delivery, only the frontend's apply step needs to be idempotent, which is cheaper to get right.
- **No cross-range ordering guarantee** — deliberately out of scope. Each `Range` is an independent "incident universe" (`PRODUCT.md` §2.2); nothing in the product requires ordering `Range` A's events relative to `Range` B's.

## Alternatives Considered

**Plain REST polling** (frontend periodically `GET`s current state per `Range`/`World`).
Rejected. Latency mismatch with the intended spatial-UI feel (an `Asset` should appear roughly when it actually finishes provisioning, not up to one poll-interval later), and three UI spaces polling independently multiplies query load for no benefit over a push model. Also doesn't naturally give the "materializes only after the event arrives" property — polling encourages exactly the anti-pattern of inferring state from a snapshot rather than reacting to an event.

**Direct Postgres subscription to the frontend** (e.g., `LISTEN`/`NOTIFY` exposed straight through to browser clients).
Rejected. Couples the frontend to the database schema and connection model directly, bypasses any auth/shaping boundary `apps/api` would otherwise provide, and gives up the one place (`packages/events`' envelope) where a stable, versioned, cross-language contract is defined. `LISTEN`/`NOTIFY` also has its own payload size limits and no per-client backlog — no better than Redis pub-sub on the durability problem this ADR exists to solve, while being worse on encapsulation.

**GraphQL subscriptions.**
Rejected for M1. Would require introducing a GraphQL layer nothing else in the stack currently uses — `Decisions.md` has already committed to Pydantic contracts + REST/event delivery, and adding a second API paradigm on top purely for subscriptions is unjustified complexity under hackathon time pressure. Revisit only if a future milestone's frontend needs richer ad hoc querying that this event-stream model can't serve.

**Optimistic client-side updates** (UI predicts the result of an action immediately, reconciles when the real event arrives).
Rejected outright — this is the literal anti-pattern the product spec forbids ("never invented"). Even setting the product rule aside, it introduces a reconciliation failure mode (what does the UI do when the prediction was wrong — a `World` fork that the scheduler actually rejects for budget reasons?) that has no upside here: these are not latency-sensitive keystroke-level interactions where optimistic UI earns its complexity, they're infrequent, consequential actions (fork a world, apply a remediation) where waiting a few hundred milliseconds for a real confirmation is the correct UX, not a compromise.

**Full event-sourcing framework / Kafka now, instead of the Postgres `event_log` bridge.**
Deferred, per `Decisions.md` #4, until multi-worker fan-out actually needs replay/partitioning at a scale Redis pub-sub + a Postgres table can't serve. The `event_log` table designed here is the concrete interim mechanism that gets replay-safety now without pulling in Kafka's operational overhead this week. When ADR-003 is written and a Kafka migration happens, this ADR's gateway contract (replay-then-live-tail over one WS endpoint) is designed to survive that swap with only the transport underneath changing — the frontend contract doesn't need to change.

## Consequences

**Positive:**
- Satisfies the "never invented" rule by construction: the store's only mutation path is applying a received, durably-logged event.
- One gateway contract serves both "fresh client" and "reconnecting client" cases — no separate snapshot API to keep in sync with the event stream.
- Idempotent, ordered apply on the frontend means producers don't need exactly-once delivery guarantees — simpler on the backend side, where correctness matters more (policy/safety boundary work already has enough invariants to hold per `PRODUCT.md` §5).
- Works with the already-locked stack (`Decisions.md` #4, #5, #6) with no new infrastructure dependency — the `event_log` table lives in the Postgres already being stood up.
- Sets up a clean migration path to Kafka (ADR-003) later without a frontend contract change.

**Negative / accepted debt:**
- Every state transition now does a synchronous durable write (`event_log` append) on the hot path before publish — write amplification versus publishing to Redis alone. Acceptable at M1's event volume (single-digit concurrent `Range`s/`World`s); would need revisiting if `packages/scheduler`'s decision frequency or `packages/evidence`'s collection rate gets high enough to make this a bottleneck (same revisit trigger as ADR-002's Python-perf note).
- The WS gateway in `apps/api` is a new component that needs an explicit owner for implementation — flagged here and in `PRODUCT.md` §6; Agent 14 (`apps/api`) and Agent 15 (`packages/events`) need to agree on exactly where the replay query + subscribe-handover logic (§2 above) lives (likely `apps/api`, calling into `packages/events` for the Redis subscribe and directly querying `event_log` for replay).
- No cross-range consistency guarantees (by design, see §5) — if a future feature needs to reason about ordering *across* Ranges, this ADR does not provide it and would need revisiting.
- The per-range `seq` counter needs a concurrency-safe assignment strategy (Postgres sequence scoped per range, or an advisory lock) — a real implementation detail left to Agent 15, but flagged here because getting it wrong (e.g., a naive `MAX(seq)+1` read-then-write) breaks the ordering guarantee this whole design depends on.

**Revisit trigger:** event volume or fan-out needs (many concurrent `World`s, many UI clients per `Range`) outgrow Redis pub-sub + Postgres `event_log` — at that point, ADR-003's Kafka migration slots in underneath this ADR's gateway contract without the frontend needing to change.
