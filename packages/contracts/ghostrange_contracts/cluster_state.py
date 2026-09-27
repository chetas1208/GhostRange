"""ClusterStateV1 / WorldStateV1 / BudgetStateV1: additive M2 models proposed
by Agent 10 (GhostScheduler) to supply the *live, time-varying* inputs the
scheduler needs that no existing V1 model carries.

These are strictly additive: no existing field on any frozen V1 model is
renamed, removed, or retyped. They are new top-level models, following the
same ``VersionedModel``/``schema_version`` convention as everything else in
this package (see ``_base.py``).

Why these three and not fewer/more (see ``packages/scheduler/README.md``
for the full design rationale, this is the short version):

- ``ClusterStateV1`` — what the compute fleet looks like *right now*:
  capacity/in-use per ``ResourceClass`` (for resource-class selection and
  parallelism decisions), a placeholder Vultr rate card (for cost
  estimation — see ``docs/research/VULTR.md``), and rolling per-``TaskType``
  duration statistics (for straggler detection per ``SPECULATION.md`` §B).
  Scoped to a Range's whole compute fleet, not one World, since compute
  workers are shared across a Range's Worlds.
- ``WorldStateV1`` — what one investigation branch (World) looks like right
  now: every task's status (for dependency-satisfaction checks) and, for
  any task currently RUNNING, live progress telemetry (elapsed time, cost
  spent, evidence accumulated, and live re-estimates of *remaining* cost/
  evidence-gain) — this is the direct input to the ``ADAPTIVE_COMPUTE.md``
  §3.1 stopping function, which explicitly requires "remaining" not
  "total-so-far" estimates.
- ``BudgetStateV1`` — wraps the existing (frozen) ``BudgetV1`` policy object
  with one additive concept: *committed* spend (decisions already issued
  by the scheduler whose cost hasn't yet posted to ``BudgetV1.spent_cost_usd``
  because execution hasn't settled). Without this, a burst of scheduling
  decisions issued in the same tick could all see stale headroom and
  collectively overspend before any of them settles. This directly feeds
  the budget-conditioned stopping floor from ``ADAPTIVE_COMPUTE.md`` §3.1.

Proposed for reconciliation into the shared ``packages/contracts`` package
per ``docs/milestones/M2_COORDINATION.md``'s contract-change protocol (this
is the "propose the additive field/model in your report" step; Agent 01
reconciles). Other agents needing cluster/world/budget snapshots for their
own M2 work are welcome to reuse these rather than inventing parallel ones.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field, field_validator

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ResourceClass, TaskStatus, TaskType
from .policy import BudgetV1


class TaskDurationStatsV1(VersionedModel):
    """Rolling per-``TaskType`` duration statistics, used for relative
    (peer-cohort) straggler detection per ``SPECULATION.md`` §B rather than
    a single global absolute timeout.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    task_type: TaskType
    p50_seconds: float = Field(..., ge=0)
    p90_seconds: float = Field(..., ge=0)
    sample_count: int = Field(..., ge=0)

    @field_validator("p90_seconds")
    @classmethod
    def _p90_at_least_p50(cls, v: float, info) -> float:
        p50 = info.data.get("p50_seconds")
        if p50 is not None and v < p50:
            raise ValueError("p90_seconds must be >= p50_seconds")
        return v


class BudgetStateV1(VersionedModel):
    """Live budget snapshot: the frozen ``BudgetV1`` policy plus in-flight
    commitments not yet reflected in ``BudgetV1.spent_cost_usd``.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    budget: BudgetV1
    committed_cost_usd: float = Field(
        default=0.0,
        ge=0,
        description="Cost of scheduler decisions already issued this tick/window "
        "whose spend has not yet posted to budget.spent_cost_usd.",
    )
    as_of: AwareDatetime = Field(default_factory=utc_now)

    @property
    def effective_spent_usd(self) -> float:
        return self.budget.spent_cost_usd + self.committed_cost_usd

    @property
    def effective_remaining_usd(self) -> float:
        return max(0.0, self.budget.max_total_cost_usd - self.effective_spent_usd)

    @property
    def headroom_fraction(self) -> float:
        """Remaining budget as a fraction of the total cap, in [0, 1]."""
        if self.budget.max_total_cost_usd <= 0:
            return 0.0
        return max(0.0, min(1.0, self.effective_remaining_usd / self.budget.max_total_cost_usd))

    @property
    def is_exhausted(self) -> bool:
        if self.budget.hard_stop:
            return self.effective_spent_usd >= self.budget.max_total_cost_usd
        return self.budget.is_exhausted


class ClusterStateV1(VersionedModel):
    """Snapshot of a Range's compute fleet at decision time: capacity,
    in-use slots, a cost-model rate card, and duration stats — everything
    GhostScheduler needs for resource-class selection, parallelism, cost
    estimation, and straggler detection that isn't carried by any single
    ``ComputeWorkerV1``.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    range_id: Id
    as_of: AwareDatetime = Field(default_factory=utc_now)

    budget: Optional[BudgetStateV1] = Field(
        default=None,
        description="Live budget snapshot for this Range's compute spend, if a budget "
        "is configured. Carried on ClusterStateV1 (rather than as a fourth argument "
        "to schedule()) because budget is scoped to the whole Range's compute fleet, "
        "same scope as everything else on this model — see BUDGET_EXHAUSTED handling "
        "in ghostrange_scheduler.",
    )
    capacity: dict[ResourceClass, int] = Field(
        default_factory=dict,
        description="Total provisionable slots per resource class, e.g. how many "
        "concurrent CPU_MEDIUM workers this Range's plan/policy allows.",
    )
    in_use: dict[ResourceClass, int] = Field(
        default_factory=dict,
        description="Slots of each resource class currently occupied by running tasks.",
    )
    rate_card_usd_per_hour: dict[ResourceClass, float] = Field(
        default_factory=dict,
        description="Known/observed hourly cost per resource class for this cluster "
        "(e.g. averaged from ComputeWorkerV1.cost_per_hour_usd of active workers of "
        "that class). Falls back to a documented placeholder rate card in "
        "ghostrange_scheduler.cost when absent for a class.",
    )
    duration_stats: dict[TaskType, TaskDurationStatsV1] = Field(
        default_factory=dict,
        description="Rolling p50/p90 duration per task_type, for relative straggler "
        "detection (SPECULATION.md §B).",
    )

    def available_slots(self, resource_class: ResourceClass) -> int:
        return max(0, self.capacity.get(resource_class, 0) - self.in_use.get(resource_class, 0))

    def has_gpu_capacity(self) -> bool:
        return self.available_slots(ResourceClass.GPU_SMALL) > 0 or self.available_slots(
            ResourceClass.GPU_LARGE
        ) > 0


class TaskProgressV1(VersionedModel):
    """Live telemetry for one currently-RUNNING task, re-estimated as it
    executes (the Pollux-style "don't trust the static upfront estimate"
    argument from ``SCHEDULING.md`` §5). ``remaining_*`` fields are what
    ``ADAPTIVE_COMPUTE.md`` §3.1's stopping function calls ``g_hat(t)``/
    ``c_hat(t)`` — explicitly *remaining*, not total-so-far, so sunk cost
    never enters the stop/continue comparison.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    task_id: Id
    started_at: AwareDatetime
    elapsed_seconds: float = Field(..., ge=0)
    cost_spent_usd: float = Field(..., ge=0)
    evidence_accumulated: float = Field(
        default=0.0, ge=0, description="Cumulative realized evidence gain observed so far."
    )
    remaining_cost_estimate_usd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Live re-estimate of remaining cost to completion (c_hat(t)). "
        "Falls back to (task.estimated_cost_usd - cost_spent_usd), floored at 0, "
        "when not supplied.",
    )
    remaining_evidence_gain_estimate: Optional[float] = Field(
        default=None,
        ge=0,
        description="Live re-estimate of remaining expected evidence gain (g_hat(t)). "
        "Falls back to task.expected_evidence_gain when not supplied.",
    )


class WorldStateV1(VersionedModel):
    """Snapshot of one investigation branch (World): every known task's
    status (dependency-satisfaction input) plus live progress for any
    RUNNING tasks (stopping-function input).
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    range_id: Id
    as_of: AwareDatetime = Field(default_factory=utc_now)

    task_status: dict[Id, TaskStatus] = Field(
        default_factory=dict,
        description="Status of every task known in this World, keyed by task id — "
        "used to evaluate whether a task's dependencies are satisfied.",
    )
    downstream_dependents: dict[Id, list[Id]] = Field(
        default_factory=dict,
        description="task_id -> ids of tasks that directly depend on it (the inverse "
        "of TaskV1.dependencies), used for dependency_criticality and the "
        "Function-C downstream_blocked_without(t) veto query. Deterministic graph "
        "data, not a statistical estimate — typically derived once from an "
        "ExecutionGraphV1 by execution-graph and carried here for the scheduler.",
    )
    progress: dict[Id, TaskProgressV1] = Field(
        default_factory=dict,
        description="Live telemetry for currently-RUNNING tasks, keyed by task id.",
    )

    def dependencies_satisfied(self, dependency_ids: list[Id]) -> bool:
        """A dependency with unknown status (not present in task_status)
        is treated as unsatisfied — fail closed, never schedule ahead of
        an unknown state.
        """
        return all(self.task_status.get(dep_id) == TaskStatus.COMPLETED for dep_id in dependency_ids)

    def downstream_blocked_without(self, task_id: Id) -> bool:
        """True iff some direct dependent of ``task_id`` is not yet
        COMPLETED/CANCELLED/FAILED — i.e. something is still waiting on
        this task. Exact graph query per ADAPTIVE_COMPUTE.md §3.3, not a
        heuristic.
        """
        terminal = {TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED}
        for dependent_id in self.downstream_dependents.get(task_id, []):
            if self.task_status.get(dependent_id) not in terminal:
                return True
        return False

    def count_downstream_pending(self, task_id: Id) -> int:
        """How many direct dependents of ``task_id`` are not yet
        COMPLETED/CANCELLED/FAILED. Same terminal-state rule as
        ``downstream_blocked_without``, but a count rather than a
        boolean — this is the raw input to
        ``ghostrange_scheduler.normalize.dependency_criticality_from_downstream_count``.
        """
        terminal = {TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED}
        return sum(
            1
            for dependent_id in self.downstream_dependents.get(task_id, [])
            if self.task_status.get(dependent_id) not in terminal
        )


__all__ = [
    "TaskDurationStatsV1",
    "BudgetStateV1",
    "ClusterStateV1",
    "TaskProgressV1",
    "WorldStateV1",
]
