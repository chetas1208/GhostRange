"""Parallelism decision: how many concurrent execution slots of its target
ResourceClass GhostScheduler grants a task at this tick.

This is deliberately narrow and NOT a speculative-execution or
world-forking mechanism (both explicitly out of M2 scope per the task
brief). It answers one question: "given this task's type and the
cluster's current free capacity for its resource class, must it run
alone, or can peers of the same class run alongside it right now."

Two task types are hard-forced to serialize regardless of free capacity:
PROVISION and TEARDOWN. Rationale: these mutate a World's underlying
infrastructure state (create/destroy assets); running two of them
concurrently against the same World risks a race on infra that has no
optimistic-concurrency story yet in range-runtime (Agent 04's package,
out of this package's ownership) -- serializing them is the conservative,
explainable default until range-runtime proves it's safe to relax.
"""

from __future__ import annotations

from ghostrange_contracts.cluster_state import ClusterStateV1
from ghostrange_contracts.enums import ResourceClass, TaskType

SERIALIZING_TASK_TYPES = frozenset({TaskType.PROVISION, TaskType.TEARDOWN})

# Upper bound on how much concurrency the scheduler will grant a single
# task in one decision, independent of raw free capacity -- prevents one
# task from being handed the cluster's entire remaining headroom in a
# single decision. Tunable; M2 has one range with modest services (per
# the task brief), so a small cap is appropriate for now.
MAX_PARALLELISM_CAP = 4


def decide_parallelism(
    task_type: TaskType,
    resource_class: ResourceClass,
    cluster_state: ClusterStateV1 | None,
) -> int:
    if task_type in SERIALIZING_TASK_TYPES:
        return 1

    if cluster_state is None:
        return 1

    available = cluster_state.available_slots(resource_class)
    return max(1, min(available, MAX_PARALLELISM_CAP))


__all__ = ["SERIALIZING_TASK_TYPES", "MAX_PARALLELISM_CAP", "decide_parallelism"]
