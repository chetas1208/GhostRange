# ghostrange-contracts

Single source of truth for GhostRange domain model shapes. Every other
package (`range-runtime`, `scheduler`, `evidence`, `execution-graph`,
`vultr-control`, `adversary-adapter`, `packages/events`, `apps/api`) imports
its domain types from here instead of redefining them. `apps/web` consumes
the exported JSON Schema (see below) rather than importing Python directly.

## Install

From the repo root, in a virtualenv:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e packages/contracts
# with test deps:
pip install -e "packages/contracts[dev]"
```

## Versioning convention

Every domain model that is persisted, sent over the wire, or referenced
across a package boundary is a *versioned* model:

- Its class name carries an explicit version suffix: `RangeSpecV1`,
  `TaskV1`, `SchedulerDecisionV1`, `EvidenceV1`, `WorldV1`, ...
- It subclasses `ghostrange_contracts._base.VersionedModel`, which requires
  a `schema_version: Literal["1"] = "1"` field. This means the version is
  visible in the *serialized JSON itself*, not just in the Python type —
  important because events get replayed from Redis and evidence gets read
  back out of Postgres long after the code that wrote it may have changed.

**When a model's shape changes in a backwards-incompatible way: do not
mutate the existing class.** Add a new class (`TaskV2`) alongside the old
one, and a migration function if old data needs to be read forward. Old
serialized data must stay valid and loadable forever — that's the whole
point of stamping `schema_version` into the payload.

A few small nested value objects embedded only inside a versioned parent
(e.g. `NetworkSpecV1`, `AssetSpecV1` inside `RangeSpecV1`) carry the `V1`
suffix for shape-alignment but do not duplicate `schema_version` — they are
never deserialized independently of their parent.

## Importing from other packages

```python
from ghostrange_contracts import RangeSpecV1, TaskV1, SchedulerDecisionV1
# or, for the module directly:
from ghostrange_contracts.range import RangeSpecV1
from ghostrange_contracts.task import TaskV1
```

All public models and enums are also re-exported from the package root
(`ghostrange_contracts/__init__.py`); either import path is supported and
tested.

## Module map

| Module | Models |
|---|---|
| `range.py` | `RangeSpecV1`, `RangeV1`, `NetworkSpecV1`, `AssetSpecV1`, the `RangeLifecycleState` transition table (`can_transition`, `assert_transition`) |
| `world.py` | `WorldV1`, `WorldForkV1` |
| `asset.py` | `NetworkV1`, `AssetV1`, `ServiceV1` (runtime-materialized, vs. the `*SpecV1` declarative versions in `range.py`) |
| `agent.py` | `AgentV1` |
| `task.py` | `TaskV1`, `ResourceProfileV1`, `RetryPolicyV1`, `SpeculationPolicyV1` |
| `execution_graph.py` | `ExecutionGraphV1`, `DependencyEdgeV1`, `ExecutionRecordV1` |
| `compute.py` | `ComputeWorkerV1` |
| `scheduler.py` | `SchedulerDecisionV1` |
| `hypothesis.py` | `HypothesisV1`, `RemediationV1`, `AttackAttemptV1` |
| `verification.py` | `VerificationV1`, `ObservationV1` |
| `evidence.py` | `ClaimV1`, `EvidenceV1`, `ArtifactV1` |
| `policy.py` | `PolicyV1`, `BudgetV1` |
| `enums.py` | every shared enum (`RangeLifecycleState`, `ReasonCode`, `ResourceClass`, ...) |
| `_base.py` | `GhostRangeModel`, `VersionedModel`, `Id`, `new_id()`, `utc_now()` |

## Range lifecycle state machine

`RangeLifecycleState` and `RANGE_LIFECYCLE_TRANSITIONS` in `range.py` are
the **authoritative** state machine, reconciling the linear happy-path list
from the product spec with the reality that things fail or get torn down
early:

```
REQUESTED -> PLANNING -> PROVISIONING -> BOOTING -> READY
  -> EXECUTING <-> VERIFYING -> STOPPING -> DESTROYING -> DESTROYED

FAILED is reachable from every non-terminal state.
DESTROYED and FAILED are the only terminal states.
```

Use `can_transition(current, target) -> bool` to check, or
`assert_transition(current, target)` to raise `ValueError` on an illegal
transition. `packages/execution-graph` and the security-boundary
policy-check service must call this before persisting any Range state
change rather than re-deriving their own copy of this table.

## JSON Schema export

```bash
python -m ghostrange_contracts.export_schema
# writes packages/contracts/schemas/<ModelName>.json for every model
```

This is what CI diffs the hand-written `apps/web` TypeScript types against
in M1 (no runtime codegen yet — tracked as a follow-up per Decisions.md
#3). Re-run this and commit the diff whenever a model shape changes.

## Tests

```bash
pip install -e "packages/contracts[dev]"
pytest packages/contracts/tests
```

Tests cover: valid instances construct, invalid ones raise `ValidationError`
(or `ValueError` for the lifecycle transition guard), and schema export
runs without error for every model.
