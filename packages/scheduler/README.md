# ghostrange-scheduler — GhostScheduler v1

Owner: Agent 10. Scope: M2 §21-23. Deterministic, explainable compute
scheduling for GhostRange investigation tasks.

```
schedule(task: TaskV1, cluster_state: ClusterStateV1, investigation_state: WorldStateV1) -> SchedulerDecisionV1
```

**Explicitly not built here, and will never be:** reinforcement learning, a
neural scheduler, or an LLM directly deciding infrastructure placement.
Every branch in `scheduler.py` is a plain if/else over normalized numeric
factors and closed-form formulas. Every decision resolves to one or more
of the 10 already-locked `ReasonCode` values
(`ghostrange_contracts.enums.ReasonCode`) — no new codes were invented.

## Contents

- [New contracts models (additive, proposed)](#new-contracts-models-additive-proposed)
- [The priority formula](#the-priority-formula)
- [The stopping function](#the-stopping-function)
- [Cost estimation](#cost-estimation)
- [Resource-class selection](#resource-class-selection)
- [Parallelism decision](#parallelism-decision)
- [Dependency awareness](#dependency-awareness)
- [Decision precedence, top to bottom](#decision-precedence-top-to-bottom)
- [Benchmark fixtures](#benchmark-fixtures)
- [Known simplifications / deviations](#known-simplifications--deviations-flagged-honestly)
- [Out of scope for M2](#out-of-scope-for-m2-not-built-interfaces-dont-block-it-later)

## New contracts models (additive, proposed)

`schedule()`'s three parameters need live, time-varying state that no
existing (frozen) V1 model carries. Added additively to
`packages/contracts/ghostrange_contracts/cluster_state.py` — no existing
field on any other model was renamed, removed, or retyped:

| Model | What it is | Why it's needed |
|---|---|---|
| `ClusterStateV1` | Snapshot of a Range's compute fleet: capacity/in-use per `ResourceClass`, a Vultr rate card, per-`TaskType` duration stats, and an optional `BudgetStateV1`. | Resource-class selection, parallelism, cost estimation, straggler detection, budget gating. |
| `WorldStateV1` | Snapshot of one investigation branch: every task's status, the inverse-dependency graph (`downstream_dependents`), and live `TaskProgressV1` for RUNNING tasks. | Dependency-satisfaction checks, Function C's `downstream_blocked_without` query, stopping-function inputs. |
| `BudgetStateV1` | Wraps the frozen `BudgetV1` with `committed_cost_usd` (spend already decided but not yet posted). | Prevents a burst of decisions in one tick from all seeing stale headroom; feeds the budget-conditioned stopping floor. |
| `TaskProgressV1` | Per-task live telemetry: elapsed time, cost spent, evidence accumulated, and **remaining** cost/evidence-gain re-estimates. | Direct `g_hat(t)`/`c_hat(t)` input to the stopping function — explicitly *remaining*, not total-so-far, so sunk cost never enters the comparison. |
| `TaskDurationStatsV1` | Rolling p50/p90 duration per `TaskType`. | Relative (not absolute-timeout) straggler detection, per `SPECULATION.md` §B. |

Per `docs/milestones/M2_COORDINATION.md`'s contract-change protocol, this
is the "propose the additive field/model in your report" step — Agent 01
reconciles. These are registered in `ghostrange_contracts/__init__.py`
and schema-exported (`packages/contracts/schemas/{ClusterStateV1,WorldStateV1,BudgetStateV1,TaskProgressV1,TaskDurationStatsV1}.json`)
so other M2 agents can reuse them rather than inventing parallel state models.

## The priority formula

Implemented exactly as `docs/research/ADAPTIVE_COMPUTE.md` §4.3 proposes,
in `priority.py`:

```
value_score = w1 * log(1 + expected_evidence_gain) + w2 * log(1 + uncertainty)
boost       = 1 + w3 * security_risk + w4 * dependency_criticality
priority    = (value_score * boost) / max(estimated_cost_usd, cost_floor)
```

Default weights `w1=w2=w3=w4=0.5` (equal starting weight, no calibration
data exists yet — one range, modest services). `cost_floor = $0.01`.

**Why this formula and not the naive candidate** (`expected_evidence_gain
* security_risk * uncertainty_reduction * dependency_criticality /
estimated_execution_cost`), per the doc's own critique (§4.1), which this
implementation verifies by test (`test_priority.py`):

1. **Zero-collapse.** The naive formula multiplies four factors — one
   legitimately-zero factor (e.g. unmeasured `security_risk`) zeroes the
   *entire* score regardless of the other three. `log(1+x)` + summation
   (not multiplication) inside `value_score` means one weak factor
   *reduces*, never *annihilates*, the score
   (`test_value_score_zero_evidence_gain_does_not_zero_the_whole_term`).
2. **Unbounded blowup.** `estimated_execution_cost` in a bare denominator
   sends priority to infinity as cost→0. `max(cost, cost_floor)` bounds it
   (`test_compute_priority_cost_floor_prevents_unbounded_blowup`).
3. **No normalization contract.** All four inputs are forced into [0,1]
   *before* they reach this formula — see [normalize.py](#new-contracts-models-additive-proposed)
   below — so whichever factor has the widest raw range can't silently
   dominate ranking.
4. **Risk/dependency as boosts, not gates.** `boost` is additive with a
   floor of 1 (`test_boost_floor_is_exactly_one_when_risk_and_dependency_are_zero`):
   a task with zero measured risk/dependency is priced at its plain
   `value_score`, not zeroed out, and dependency criticality alone can
   never "manufacture value" for a task with zero evidence gain (the
   doc's explicitly-rejected alternative, a pure ratio-of-sums, would
   allow that).

`priority` (a float) is scaled ×100 and rounded into
`SchedulerDecisionV1.priority` (an int, per the frozen contract);
`expected_value = value_score * boost` maps directly onto
`SchedulerDecisionV1.expected_value`'s documented meaning ("unitless
expected-evidence-value score").

### The [0,1] normalization boundary (`normalize.py`)

ADAPTIVE_COMPUTE.md §4.1.4 calls this "the single most urgent,
cheapest-to-fix issue" and explicitly recommends a Pydantic
`@field_validator`. `NormalizedPriorityFactorsV1` is that validator,
implemented for real: every one of its four fields is guaranteed in
[0,1] by construction (clamped on the way in via a `mode="before"`
validator, then bounds-checked by `Field(ge=0, le=1)`).

The ideal fix is upstream, on `TaskV1` itself — bound
`expected_evidence_gain` to [0,1] and add first-class
`security_risk`/`dependency_criticality` float fields. `TaskV1` is frozen
for M2 wave 1 and shared by many agents, so that's a proposal for Agent
01/14 to reconcile, not something silently added here. Until it lands,
this module is the enforced boundary and the two missing raw inputs are
derived deterministically from what `TaskV1`/`WorldStateV1` already have:

- `security_risk` ← `TaskV1.security_criticality` (categorical) via a
  fixed placeholder mapping: LOW=0.25, MEDIUM=0.5, HIGH=0.75, CRITICAL=1.0.
- `dependency_criticality` ← count of not-yet-terminal direct downstream
  dependents (`WorldStateV1.count_downstream_pending`), saturating at 1.0
  at 3+ pending dependents (`DEPENDENCY_CRITICALITY_SATURATION_COUNT`).
- `uncertainty` is used as-is from `TaskV1.uncertainty` (already
  contract-bound to [0,1]) as GhostScheduler v1's proxy for the doc's
  `uncertainty_reduction` term — `TaskV1` has no separate
  "expected uncertainty reduction if this task runs" field yet; "current
  uncertainty" is the closest available signal (a task addressing high
  uncertainty has more room to reduce it). Flagged as a proposed additive
  `TaskV1` field for a future iteration, not invented here.

## The stopping function

`docs/research/ADAPTIVE_COMPUTE.md` §3 gives three candidate stopping
functions and explicitly recommends Function A as the v0/v1 default. This
package implements **Function A only** (per the task brief: "implement
ONE of the three... recommend Option A"), in `stopping.py`:

```
marginal_ratio(t) = (g_hat(t) * risk(t) * dep(t)) / max(c_hat(t), c_min)
STOP if marginal_ratio(t) < floor_threshold
```

- `g_hat(t)` / `c_hat(t)` — live *remaining* evidence gain / cost
  re-estimates, from `WorldStateV1.progress[task_id].remaining_*`
  (falling back to `task.expected_evidence_gain` /
  `task.estimated_cost_usd - cost_spent_usd` when not supplied). Sunk
  cost never enters the comparison, by construction.
- `risk(t)`, `dep(t)` — the same normalized `security_risk`/
  `dependency_criticality` factors used by the priority formula.
- `floor_threshold` is **budget-conditioned**, per the doc's explicit
  suggestion: it rises as budget headroom shrinks
  (`floor_threshold(budget_state)`, `BUDGET_FLOOR_SENSITIVITY=4.0`), so
  "the scheduler gets pickier automatically" as money runs low — a
  concrete, testable link between `BudgetStateV1` and stopping behavior
  the naive priority formula has no mechanism for at all.

**Why Function A and not B/C standalone:** the doc itself recommends A as
the default ("fewest moving parts, requires no probability distributions
or posteriors... every term is independently inspectable"). Function B
(realized-slope detector) and the §3.4 learned-estimator forward-compat
interface are **not implemented** in v1 — see
[Known simplifications](#known-simplifications--deviations-flagged-honestly).

### Function C (dependency/budget veto) — also implemented

`effective_stop()` implements §3.3's veto layer verbatim, because it's
cheap, deterministic boolean logic needed to get **precedence** right:

```
effective_stop = stop_recommended
                  AND NOT (dep >= dependency_critical_threshold AND downstream_blocked_without)
                  AND NOT budget_exhausted_override   # forces stop, overrides everything
```

`test_effective_stop_precedence_budget_beats_dependency_veto_explicitly`
asserts this exact ordering — the doc warns this precedence is "easy to
implement backwards", so it's centralized in one tested function instead
of ad hoc if/else ordering in `scheduler.py`.

### Known deviation: the zero-factor floor

`marginal_ratio` is a **strict three-way product**. `dependency_criticality`
is legitimately 0 for the common case of a leaf task with no downstream
dependents (most tasks have none). A literal implementation would
therefore collapse the ratio to 0 — and recommend stopping — for
*almost every ordinary task*, independent of how valuable `g_hat` is.
This is the exact zero-collapse failure mode §4.1.2 identifies for the
*priority* formula's multiplicative shape; the doc just doesn't carry
that critique over to Function A's identical shape (§3.1 never discusses
`risk(t)`/`dep(t)` == 0 as a case), which reads as an oversight rather
than a deliberate choice.

**Mitigation (`ZERO_FACTOR_FLOOR = 0.1`, in `stopping.py`):** `risk`/`dep`
are floored at 0.1 before multiplying — an absent/unmeasured signal acts
as "weak", not "definitely zero out everything". `g_hat`/`c_hat` are
*not* floored the same way: a genuinely-zero remaining evidence gain
should still drive the ratio to zero (`test_marginal_voi_ratio_genuinely_zero_gain_still_drives_ratio_to_zero`).
This is a narrow, tested, explicitly-flagged deviation from the literal
pseudocode — not the log-sum redesign §4 warns not to re-apply here; the
formula's shape (product over cost, floored) is unchanged.

## Cost estimation

`cost.py`'s `estimate_cost_usd(resource_class, duration_seconds,
cluster_state)` = `hourly_rate * (duration_seconds / 3600)`.
`cluster_state.rate_card_usd_per_hour` (observed pricing) always wins
when present; otherwise falls back to `DEFAULT_RATE_CARD_USD_PER_HOUR`:

| ResourceClass | $/hr | Source |
|---|---|---|
| CPU_SMALL | 0.0042 | **Real**, derived from `docs/research/VULTR.md` §1: "$2.50-3.50/mo (1 vCPU/512MB)" → $3/mo ÷ (24×30)h |
| CPU_MEDIUM | 0.03 | **PLACEHOLDER** — no specific Vultr plan cited in VULTR.md for this tier |
| CPU_LARGE | 0.12 | **PLACEHOLDER** — interpolated |
| GPU_SMALL | 1.00 | **PLACEHOLDER** — VULTR.md only cites the full 8-GPU H100 chassis rate, no single/fractional-GPU plan |
| GPU_LARGE | 2.99 | **Real**, from VULTR.md §2: $23.92/hr chassis ÷ 8 GPUs |

Every decision whose resource class used a placeholder rate carries a
note in `SchedulerDecisionV1.notes` saying so. Whoever wires live Vultr
pricing (Agent 02, `packages/vultr-control`) should feed real per-class
rates into `ClusterStateV1.rate_card_usd_per_hour`, which always takes
precedence over this fallback table.

## Resource-class selection

`resource_selection.py` maps `TaskV1.resource_profile` onto one of the
**five `ResourceClass` values the contracts layer actually defines**
today: `CPU_SMALL`, `CPU_MEDIUM`, `CPU_LARGE`, `GPU_SMALL`, `GPU_LARGE`.

`SERVERLESS_INFERENCE` is deliberately **not** added to the enum: it
doesn't exist in `ghostrange_contracts.enums.ResourceClass`, and nothing
in `TaskV1`/`ResourceProfileV1` today distinguishes "wants inference"
from "wants a GPU box" — adding it now would be speculative, not
additive-for-a-consumer. Revisit when Agent 11 (M2 wave 2, "Vultr
Serverless Inference planner") defines an inference-shaped task type.

`preferred_resource_class` (if set) always wins. Otherwise, CPU sizing is
by `cpu_cores`/`memory_gb` threshold (`CPU_SMALL_MAX_CORES=2`, etc. — see
module for exact thresholds, all documented tunable constants, not
fitted). If `gpu_required` and the cluster has zero free GPU capacity,
falls back to the best CPU class for the task's shape and fires
`GPU_NOT_JUSTIFIED`; otherwise fires `GPU_ACCELERATION_EXPECTED`.

Note on reusing `GPU_NOT_JUSTIFIED`: `SCHEDULING.md` §3 frames this code
around *runtime* GPU-utilization introspection (a running task using
<15% of a GPU it was given) — that live-telemetry loop is out of M2
scope here (no runtime feedback loop, see below). This module instead
fires the same code faithfully for the one in-scope case it fits: the
cluster cannot currently justify giving this task a GPU (none available).

## Parallelism decision

`parallelism.py`: `PROVISION` and `TEARDOWN` task types always serialize
(`parallelism=1`) regardless of free capacity — they mutate a World's
infrastructure state, and range-runtime (Agent 04, out of this package's
ownership) has no optimistic-concurrency story yet, so serializing is the
conservative default. Every other task type gets
`min(cluster.available_slots(resource_class), MAX_PARALLELISM_CAP=4)`,
floored at 1.

This is a placement-level concurrency grant, not a speculative-execution
mechanism — see [Out of scope](#out-of-scope-for-m2-not-built-interfaces-dont-block-it-later).

## Dependency awareness

`WorldStateV1.dependencies_satisfied(task.dependencies)` requires every
dependency to be `TaskStatus.COMPLETED`. **A dependency with unknown
status (not present in `task_status`) is treated as unsatisfied** —
fail-closed, never schedule ahead of an unknown state
(`test_unknown_dependency_status_is_treated_as_unsatisfied_fail_closed`).
An unsatisfied dependency short-circuits to a `DEPENDENCY_CRITICAL`
blocked decision (`priority=0`, `estimated_cost_usd=0.0`, short
`expiration` for quick re-evaluation) before any priority/cost/resource
math runs at all.

## Decision precedence, top to bottom

`schedule()` evaluates gates in this fixed order (see the doc's own
explicit warning that precedence "is easy to implement backwards"):

1. **`BUDGET_EXHAUSTED`** (hard ceiling — overrides everything, including dependency criticality)
2. **`DEPENDENCY_CRITICAL`** (blocked — dependencies not satisfied)
3. If `status == RUNNING` and live progress exists: the stopping function
   (→ `MARGINAL_GAIN_LOW`, or `DEPENDENCY_CRITICAL` via Function C's veto,
   or falls through to normal scheduling if the ratio clears the floor)
4. Normal decision assembly: resource class, cost, priority, parallelism,
   plus threshold-triggered `HIGH_UNCERTAINTY` / `HIGH_ASSET_RISK` /
   `DEPENDENCY_CRITICAL` / `CHEAP_INFORMATION_GAIN` / `BRANCH_LOW_VALUE` /
   `STRAGGLER_DETECTED` as applicable. A deterministic, always-true
   fallback (`CHEAP_INFORMATION_GAIN` if cost-effective, else
   `BRANCH_LOW_VALUE`) guarantees `reason_codes` is never empty (the
   contract requires `min_length=1`) without ever mislabeling an
   average factor as "HIGH_*".

## Benchmark fixtures

`ghostrange_scheduler/benchmarks.py` defines 10 representative, fully
deterministic `(TaskV1, ClusterStateV1, WorldStateV1)` scenarios with
expected reason codes/priority/resource-class, exported as `ALL_CASES`.
Reusable by any other package/test suite:

```python
from ghostrange_scheduler.benchmarks import ALL_CASES
from ghostrange_scheduler import schedule

for case in ALL_CASES:
    decision = schedule(case.task, case.cluster_state, case.world_state, now=case.now)
    assert case.expected_reason_codes <= set(decision.reason_codes)
```

Covers: an ordinary runnable task, dependency-blocked, budget-exhausted,
GPU-available, GPU-unavailable-fallback, a running task whose value has
collapsed (should stop), the same task with a dependency veto keeping it
alive, a straggling-but-still-valuable running task, high-risk +
high-uncertainty co-firing, and a `PROVISION` task's forced serialization.

## Known simplifications / deviations (flagged honestly)

Following the research docs' own FACT / OUR INTERPRETATION / OUR DESIGN
DECISION convention:

- **Only Function A is implemented.** Function B (realized-slope
  detector) and the §3.4 learned-`EvidenceGainEstimator` forward-compat
  interface are not built — out of scope per the task brief's "implement
  ONE of the three". `g_hat`/`c_hat` are consumed as plain point
  estimates from `TaskProgressV1`; nothing in this package's structure
  prevents a future estimator interface from producing them instead.
- **The zero-factor floor** (`ZERO_FACTOR_FLOOR=0.1` in `stopping.py`) —
  see above. A real, tested, narrowly-scoped deviation from the literal
  §3.1 pseudocode, not a silent one.
- **`uncertainty` doubles as an `uncertainty_reduction` proxy** — see the
  normalization section above. `TaskV1` has no separate field for this
  yet.
- **`security_risk`/`dependency_criticality` are derived, not first-class
  `TaskV1` fields.** Placeholder mappings in `normalize.py`, proposed as
  future additive `TaskV1` fields.
- **GPU-utilization runtime introspection (Gandiva-style,
  `SCHEDULING.md` §3) is not implemented** — `GPU_NOT_JUSTIFIED` fires at
  *placement* time (no GPU capacity available) rather than from live
  utilization telemetry, which requires a runtime feedback loop this
  package doesn't own.
- **Cost model uses placeholder unit costs for 3 of 5 resource classes**
  (see the cost table above) — clearly labeled, not fabricated Vultr
  pricing.
- **Placement/bin-packing (Tetris-style alignment scoring,
  `SCHEDULING.md` §2) is not implemented.** `select_resource_class`
  answers "which class", not "which specific node" — node-level packing
  is a different, unbuilt layer.

## Out of scope for M2 (not built; interfaces don't block it later)

Per the task brief, explicitly not built in this package:

- **Speculative execution engine** — no world-forking, no duplicate/
  hedged-branch spawning. `SchedulerDecisionV1.speculative` is set from
  `task.speculation_policy.enabled` as an informational passthrough only;
  nothing here decides *to fork*.
- **Large-scale autoscaling** — `ClusterStateV1.capacity` is read, never
  written; no code here provisions/deprovisions cluster capacity.
- **World-level branch pruning / multi-world allocation** — no
  cross-World comparison or allocation logic; `schedule()` reasons about
  one task at a time, one World's state at a time.

Nothing in the model shapes (`ClusterStateV1`/`WorldStateV1`/
`BudgetStateV1`) actively prevents these from being layered on later —
`WorldStateV1.progress`/`downstream_dependents` and the estimator-style
factoring in `normalize.py` were written with that forward-compatibility
in mind, per the same principle `ADAPTIVE_COMPUTE.md` §3.4 states for a
future learned estimator.

## Running the tests

```
pip install -e packages/contracts -e packages/scheduler
pytest packages/scheduler/tests -q
```

115 tests, all deterministic (no randomness, no wall-clock reads inside
any tested code path — `now` is always passed explicitly in tests).
