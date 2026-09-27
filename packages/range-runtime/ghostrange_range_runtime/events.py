"""Events this package emits, and the port it publishes them through.

See README.md "Event gaps found" for the full rationale. Short version:
``packages/events`` has no ``range.*`` events at all yet (confirmed by
reading ``names.py``/``registry.py`` directly), and that package is not
this one's to edit (M2_COORDINATION.md's ownership table: this package
owns ``packages/range-runtime`` only, ``packages/events`` is Agent 08's,
additive-only). ``RangeTransitionEventV1`` below is the proposed shape —
deliberately structured like ``ghostrange_events._base.GhostRangeEvent``
(same envelope fields) so upstreaming it later is a near-verbatim move,
not a redesign.

Where a real ``ghostrange_events`` payload already fits (this package
also owns advancing the root World's lifecycle, per PRODUCT.md §4), the
engine emits the real thing via the same ``EventSink`` — see
``engine.py``'s ``_ROOT_WORLD_EVENT_BUILDERS``.
"""

from __future__ import annotations

import uuid
from typing import Optional, Protocol, runtime_checkable

from ghostrange_contracts._base import AwareDatetime, GhostRangeModel, Id, new_id, utc_now
from ghostrange_contracts.enums import RangeLifecycleState
from pydantic import Field


class RangeTransitionEventV1(GhostRangeModel):
    """Proposed additive event: fired for every Range transition,
    including the PLANNING-internal VALIDATING/AUTHORIZED checkpoints
    (see README gap #1) where ``previous_state == new_state`` on
    purpose — that equality is exactly how a consumer distinguishes "a
    real state change" from "a milestone note within the same state"
    until the contract gains dedicated states for those sub-phases.
    """

    event_id: uuid.UUID = Field(default_factory=new_id)
    occurred_at: AwareDatetime = Field(default_factory=utc_now)
    schema_version: str = "1"

    range_id: Id
    world_id: Optional[Id] = None
    previous_state: Optional[RangeLifecycleState] = None
    new_state: RangeLifecycleState
    reason: str
    correlation_id: str


@runtime_checkable
class EventSink(Protocol):
    """The port ``RangeRuntimeEngine`` publishes events through.

    Deliberately provider-agnostic: this package does not wire the real
    Redis/Valkey transport or Postgres ``event_log`` (ADR-011) — that is
    Agent 08's deliverable. Any object with a ``publish`` method
    satisfies this, including a real transport once it exists.
    """

    def publish(self, event: object) -> None: ...


class InMemoryEventSink:
    """Records every published event in order. Used by every test in
    this package to assert on exactly what was emitted, when.
    """

    def __init__(self) -> None:
        self.events: list[object] = []

    def publish(self, event: object) -> None:
        self.events.append(event)

    def of_type(self, cls: type) -> list[object]:
        return [e for e in self.events if isinstance(e, cls)]


class LoggingEventSink:
    """A real, if minimal, default sink for a running process: logs
    every event at INFO level via the stdlib ``logging`` module. Not a
    substitute for a durable/replayable transport — just a sink that
    does something honest (as opposed to nothing) until Agent 08's
    transport lands and can be swapped in with no engine changes.
    """

    def __init__(self, logger_name: str = "ghostrange.range_runtime.events") -> None:
        import logging

        self._logger = logging.getLogger(logger_name)

    def publish(self, event: object) -> None:
        if hasattr(event, "model_dump_json"):
            self._logger.info("%s", event.model_dump_json())  # type: ignore[attr-defined]
        else:
            self._logger.info("%r", event)


__all__ = [
    "RangeTransitionEventV1",
    "EventSink",
    "InMemoryEventSink",
    "LoggingEventSink",
]
