"""ghostrange_range_runtime: the Range/World lifecycle state machine.

Drives a ``RangeSpecV1`` (``ghostrange_contracts``) through the
authoritative lifecycle defined in ``ghostrange_contracts.range``
(``RANGE_LIFECYCLE_TRANSITIONS``, ``can_transition``,
``assert_transition``) — this package imports and enforces that state
machine rather than redefining it. See ``README.md`` for the persistence
choice, the ``ComputeProvider`` port this package defines for
``packages/vultr-control``, and the additive contract/event gaps found
along the way (reported there rather than silently patched into shared
files this package does not own).
"""

from __future__ import annotations

from .engine import RangeRuntimeEngine
from .errors import (
    IllegalTransitionError,
    ProviderError,
    RangeRuntimeError,
    ValidationFailedError,
)
from .events import (
    EventSink,
    InMemoryEventSink,
    LoggingEventSink,
    RangeTransitionEventV1,
)
from .persistence import SqliteTransitionStore, TransitionRecord
from .provider import (
    ComputeProvider,
    FakeComputeProvider,
    ProviderObservation,
    ProviderState,
)
from .reconcile import ReconcileAction, ReconcileOutcome, Reconciler
from .vultr_adapter import VultrAdaptedComputeProvider

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "RangeRuntimeEngine",
    "RangeRuntimeError",
    "IllegalTransitionError",
    "ProviderError",
    "ValidationFailedError",
    "EventSink",
    "InMemoryEventSink",
    "LoggingEventSink",
    "RangeTransitionEventV1",
    "SqliteTransitionStore",
    "TransitionRecord",
    "ComputeProvider",
    "FakeComputeProvider",
    "ProviderObservation",
    "ProviderState",
    "Reconciler",
    "ReconcileAction",
    "ReconcileOutcome",
    "VultrAdaptedComputeProvider",
]
