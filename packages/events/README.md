# ghostrange-events

Event name vocabulary (`EventName`) and versioned Pydantic payload schemas
for GhostRange's Redis/Valkey pub-sub bus (Decisions.md #4). Backend
orchestration packages publish these events; `apps/web`'s 3D visualization
subscribes and renders from them.

**Hard rule for consumers:** the frontend must not materialize UI state
ahead of the event that authorizes it. Concretely: a `ComputeNode` is drawn
only after `compute.ready` arrives, never speculatively after
`compute.requested`; a World node is drawn only after `world.ready`. Event
payloads are designed to carry every id/field a consumer needs to render
without a follow-up query — if you find yourself needing to fetch more
context after receiving an event, that's a bug in the payload, file it
against this package.

## Install

This package depends on `ghostrange-contracts` (for shared enums like
`ResourceClass`, `ReasonCode`, `TaskType`) as an editable local package.
From the repo root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e packages/contracts
pip install -e packages/events
# with test deps:
pip install -e "packages/contracts[dev]" -e "packages/events[dev]"
```

Installing `packages/contracts` first (as shown) works with plain pip.
Installing both in a single `pip install -e packages/contracts -e
packages/events` command also works in modern pip, since pip resolves all
editable targets in one invocation before dependency resolution — but the
two-step order above is the one that unambiguously works everywhere and is
what CI uses.

## Shape: one flat payload per event, not an envelope wrapper

Every event is a single flat Pydantic model — envelope fields
(`event_id`, `event_name`, `occurred_at`, `schema_version`) plus the
event-specific fields, all in one JSON object on the wire. There is no
generic `Envelope[Payload]` wrapper to unwrap; a consumer pattern-matches
on `event_name` and reads fields directly.

## Usage

```python
from ghostrange_events import EventName
from ghostrange_events.registry import EVENT_REGISTRY, parse_event
from ghostrange_events.compute_events import ComputeReadyV1

# Publishing (e.g. from range-runtime after a Vultr instance boots):
event = ComputeReadyV1(
    compute_worker_id=worker.id,
    world_id=world.id,
    resource_class=worker.resource_class,
    region=worker.region,
    provider=worker.provider,
    provider_instance_id=worker.provider_instance_id,
    cost_per_hour_usd=worker.cost_per_hour_usd,
)
redis_client.publish("ghostrange.events", event.model_dump_json())

# Consuming (e.g. in apps/web's event bridge, or any Python subscriber):
raw = redis_client.get_message()  # bytes/str JSON
typed_event = parse_event(raw)  # dispatches on event_name, raises on mismatch
if typed_event.event_name == EventName.COMPUTE_READY:
    materialize_compute_node(typed_event)
```

`parse_event` raises `pydantic.ValidationError` on a payload that doesn't
match the schema its own `event_name` claims. That is intentional: a
malformed event must fail loudly on the bus, not be silently coerced.

## Event -> payload map

| EventName | Payload class | Module |
|---|---|---|
| `world.requested` | `WorldRequestedV1` | `world_events.py` |
| `world.provisioning` | `WorldProvisioningV1` | `world_events.py` |
| `world.ready` | `WorldReadyV1` | `world_events.py` |
| `world.forked` | `WorldForkedV1` | `world_events.py` |
| `world.destroyed` | `WorldDestroyedV1` | `world_events.py` |
| `task.queued` | `TaskQueuedV1` | `task_events.py` |
| `task.scheduled` | `TaskScheduledV1` | `task_events.py` |
| `task.started` | `TaskStartedV1` | `task_events.py` |
| `task.completed` | `TaskCompletedV1` | `task_events.py` |
| `task.failed` | `TaskFailedV1` | `task_events.py` |
| `task.speculated` | `TaskSpeculatedV1` | `task_events.py` |
| `agent.started` | `AgentStartedV1` | `agent_events.py` |
| `agent.action` | `AgentActionV1` | `agent_events.py` |
| `agent.completed` | `AgentCompletedV1` | `agent_events.py` |
| `evidence.created` | `EvidenceCreatedV1` | `evidence_events.py` |
| `verification.started` | `VerificationStartedV1` | `verification_events.py` |
| `verification.passed` | `VerificationPassedV1` | `verification_events.py` |
| `verification.failed` | `VerificationFailedV1` | `verification_events.py` |
| `compute.requested` | `ComputeRequestedV1` | `compute_events.py` |
| `compute.provisioning` | `ComputeProvisioningV1` | `compute_events.py` |
| `compute.ready` | `ComputeReadyV1` | `compute_events.py` |
| `compute.released` | `ComputeReleasedV1` | `compute_events.py` |
| `scheduler.decision` | `SchedulerDecisionV1Event` | `scheduler_events.py` |

`EVENT_REGISTRY` in `registry.py` is the machine-checked version of this
table (`tests/test_registry.py` asserts every `EventName` member has
exactly one entry, and that no two names accidentally share a class).

## Versioning

Same convention as `ghostrange-contracts`: a shape change that isn't
backwards-compatible gets a new class (`ComputeReadyV2`) and a new registry
entry keyed by a new `EventName` (or, if the event concept itself is
unchanged but the payload shape changed, the class is versioned but the
`EventName` string stays stable — document which in the ADR that makes the
change). Never mutate a shipped payload class in place.

## Tests

```bash
pytest packages/events/tests
```

Covers: every `EventName` maps to exactly one payload class, every payload
class's own `event_name` default matches its registry key, and every event
type round-trips through both direct `model_validate_json` and the
registry's discriminated-union `parse_event` dispatch, from both a JSON
string and a plain dict.
