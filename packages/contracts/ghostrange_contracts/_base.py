"""Shared base classes and helpers for every GhostRange contract model.

Versioning convention
----------------------
Every domain model that is persisted, sent over the wire, or referenced from
another package is a *versioned* model: its class name carries an explicit
version suffix (``RangeSpecV1``, ``TaskV1``, ``SchedulerDecisionV1``, ...) and
it also carries a ``schema_version`` field with the same information at
runtime, so a consumer that only has the serialized JSON (e.g. something
replayed from Redis or read back out of Postgres months later) can tell which
shape it is looking at without out-of-band knowledge.

When a model's shape changes in a backwards-incompatible way, do **not**
mutate the existing class: add a new class (``TaskV2``) and, if needed, a
migration function. Old serialized data stays valid and readable forever.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import ClassVar

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Common type aliases
# ---------------------------------------------------------------------------

# All identifiers in the system are UUID4. A type alias documents intent at
# call sites while remaining a real, validated UUID (not a bare str).
Id = uuid.UUID


def new_id() -> Id:
    """Generate a new random identifier for a domain object."""
    return uuid.uuid4()


def utc_now() -> datetime:
    """Return the current time, always timezone-aware in UTC.

    Every timestamp field in this package uses ``AwareDatetime`` and this
    factory, so naive datetimes (a frequent source of "is this UTC or
    local?" bugs across a distributed system) can never silently enter a
    contract model.
    """
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Base model
# ---------------------------------------------------------------------------


class GhostRangeModel(BaseModel):
    """Base class for all GhostRange contract models.

    Strictness choices are deliberate:
    - ``extra="forbid"``: a typo'd or stale field must fail loudly at
      construction time, not be silently dropped.
    - ``validate_assignment=True``: mutating a model after construction is
      re-validated, so ``task.status = "not a real status"`` fails.
    - ``frozen=False``: contract objects are dataclasses of record, not
      immutable value types; callers that need immutability should freeze
      at the call site.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class VersionedModel(GhostRangeModel):
    """Base for models that are versioned contract objects (the "V1" family).

    Subclasses MUST override ``SCHEMA_VERSION`` and declare a
    ``schema_version`` field with a ``Literal`` matching it, e.g.::

        class TaskV1(VersionedModel):
            SCHEMA_VERSION: ClassVar[str] = "1"
            schema_version: Literal["1"] = "1"
            ...
    """

    SCHEMA_VERSION: ClassVar[str] = "unset"


__all__ = [
    "Id",
    "new_id",
    "utc_now",
    "GhostRangeModel",
    "VersionedModel",
    "AwareDatetime",
    "Field",
]
