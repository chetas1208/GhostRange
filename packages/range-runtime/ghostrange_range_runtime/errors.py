"""Exceptions raised by the range-runtime engine.

``IllegalTransitionError`` subclasses ``ValueError`` deliberately: the
brief requires illegal transitions to "raise, not silently succeed," and
``ghostrange_contracts.range.assert_transition`` already raises a plain
``ValueError`` for that case. Keeping this as a ``ValueError`` subclass
means callers/tests that only know about the contracts-level function's
behavior (``pytest.raises(ValueError)``) still work unchanged when the
same check happens through the engine, while still letting callers that
want the richer type catch ``IllegalTransitionError`` specifically.
"""

from __future__ import annotations

from typing import Optional

from ghostrange_contracts._base import Id
from ghostrange_contracts.enums import RangeLifecycleState


class RangeRuntimeError(Exception):
    """Base class for all range-runtime errors."""


class IllegalTransitionError(RangeRuntimeError, ValueError):
    """Raised when a requested Range state transition is not present in
    ``RANGE_LIFECYCLE_TRANSITIONS``.
    """

    def __init__(
        self,
        range_id: Id,
        current: RangeLifecycleState,
        target: RangeLifecycleState,
        detail: Optional[str] = None,
    ) -> None:
        self.range_id = range_id
        self.current = current
        self.target = target
        message = f"illegal Range transition for {range_id}: {current.value} -> {target.value}"
        if detail:
            message = f"{message} ({detail})"
        super().__init__(message)


class ValidationFailedError(RangeRuntimeError):
    """Raised when a RangeSpec fails the VALIDATING sub-phase.

    This is a *legal* PLANNING -> FAILED transition, not a bypass of the
    state machine — it is raised by ``RangeRuntimeEngine`` after the
    FAILED transition has already been durably persisted, so the caller
    always has a record of why, not just an exception message.
    """


class ProviderError(RangeRuntimeError):
    """Raised by ``ComputeProvider`` implementations (or wrapped around
    whatever ``packages/vultr-control`` raises) to signal a provisioning
    or teardown failure the engine should react to.
    """


__all__ = [
    "RangeRuntimeError",
    "IllegalTransitionError",
    "ValidationFailedError",
    "ProviderError",
]
