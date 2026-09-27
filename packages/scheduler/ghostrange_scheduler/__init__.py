"""ghostrange_scheduler: GhostScheduler v1.

Deterministic, explainable compute scheduling for GhostRange investigation
tasks. See README.md for the full design writeup (priority formula,
stopping function, cost model, and what is deliberately out of scope for
M2).

Public surface:
- ``schedule(task, cluster_state, investigation_state) -> SchedulerDecisionV1``
  -- the scheduler's one entrypoint.
- ``ghostrange_scheduler.normalize`` -- the [0,1] normalization boundary.
- ``ghostrange_scheduler.priority`` -- the value_score/boost/priority formula.
- ``ghostrange_scheduler.stopping`` -- the VoI-ratio-with-floor stopping function.
- ``ghostrange_scheduler.cost`` -- cost estimation / rate card.
- ``ghostrange_scheduler.resource_selection`` -- ResourceClass selection.
- ``ghostrange_scheduler.parallelism`` -- parallelism decision.
- ``ghostrange_scheduler.benchmarks`` -- reusable Task/ClusterState/WorldState
  fixture scenarios with expected decisions, for this package's own tests
  and for other agents'/wave-3 testing.
"""

from .scheduler import schedule

__version__ = "0.1.0"

__all__ = ["schedule", "__version__"]
