# Speculative Execution & Straggler Mitigation Research for GhostScheduler v0

Owner: Agent 09 (Speculative Execution Researcher). Status: research complete for M1, feeds `packages/scheduler` and `packages/execution-graph`.

## Purpose and scope

This document surveys speculative execution / straggler mitigation / hedged-request literature and translates it into concrete rules for when GhostRange should speculatively fork a second remediation-candidate world before the first fully resolves, how to detect a straggler world/task, and cancellation economics (when killing a speculative branch is worth it vs. letting it finish). As with `SCHEDULING.md`, FACT / OUR INTERPRETATION / OUR DESIGN DECISION are kept separate, and uncertain recollections are flagged **[APPROXIMATE]**.

---

## 1. MapReduce speculative execution (the foundational case)

**Citation:** Dean, J., Ghemawat, S. "MapReduce: Simplified Data Processing on Large Clusters." OSDI 2004. **[Confident on venue/year/authors — this is a very well-known paper]**

**Problem:** In a large batch job split into many identical-shape tasks, a small number of tasks ("stragglers") run far slower than their peers due to hardware degradation, resource contention, or bad-machine placement, and the whole job's completion time is gated by the slowest straggler, not the average task.

**Method (FACT):** Near the end of a MapReduce job, when most tasks have finished, the master schedules **backup ("speculative") executions** of the remaining in-progress tasks on other idle machines. Whichever copy (original or backup) finishes first "wins" and its output is used; the loser is killed. The paper reports this was a simple but effective fix, triggered essentially by remaining-tasks-are-slow heuristics near job tail, not by a sophisticated statistical model.

**Experimental environment (FACT):** Google's internal cluster infrastructure circa early 2000s, batch data-processing jobs (large-scale sort, indexing, log processing).

**Principal result (FACT):** The paper states speculative execution substantially improved completion time for jobs with stragglers — I recall a headline example (a large sort benchmark) where disabling speculation measurably lengthened the tail, but I do **not** have confident recall of the exact percentage/multiplier reported, so I will not state a specific number. **[The qualitative result — meaningful tail latency reduction — is FACT; any specific percentage I might produce would be a guess, so I'm deliberately omitting one rather than fabricating precision]**

**Limitations (FACT/OUR INTERPRETATION):** This mechanism assumes tasks are *interchangeable* — running task copy B produces the exact same correct output as task copy A, just faster or slower. It's a pure latency-hiding trick for identical, side-effect-free, idempotent work. It has no notion of "the second copy might discover something different" — that's a fundamentally different problem GhostRange has and MapReduce does not.

**GhostRange relevance (OUR INTERPRETATION — important divergence):** GhostRange's "speculative fork" is NOT the MapReduce case. Two remediation candidates run against the same incident are not two copies of the *same* computation racing for the same answer — they are two *different hypotheses* that may both produce valid but different evidence. This is the single most important translation point in this document: **MapReduce speculation is redundancy-for-speed; GhostRange speculation is parallelism-for-hypothesis-coverage.** The straggler-detection *instrumentation* pattern (compare a task's progress to its peer cohort, flag outliers) is reusable; the *response* (run a duplicate and take whichever finishes) is not directly reusable, because GhostRange's "duplicate" is actually a distinct candidate whose result has independent evidentiary value even if it also happens to be slow.

**What NOT to infer:** Do not infer that killing the loser and discarding its output is the right default for GhostRange the way it is for MapReduce — a slow-but-different remediation candidate may still be the one that reveals the real evidence; only kill it when the *combined* stopping criteria in `ADAPTIVE_COMPUTE.md` say the marginal value of continuing is below cost, not merely because a sibling finished first.

**Implementation idea for GhostScheduler:** Adopt MapReduce's straggler *detection* trigger structure (see the general framing below) but split the response into two explicit branches in `execution-graph`: (a) **true-duplicate speculation** — same candidate, same task_type, re-run on a different node because of suspected bad-node/infra flakiness (MapReduce case, kill loser on completion of winner, cheap to do because outputs should be equivalent); (b) **hypothesis speculation** — a second, different remediation candidate forked early because the first is slow/uncertain (GhostRange's actual novel case, do NOT auto-kill on a "winner," subject instead to the value-of-information stopping rules).

---

## 2. Hedged requests (tail latency mitigation via redundant requests)

**Citation:** This pattern is most associated with Dean, J. & Barroso, L.A., "The Tail at Scale," Communications of the ACM, 2013. **[Reasonably confident on venue/authors/year — this is a well-known industry paper; the specific "hedged request" terminology and mechanism I describe below is FACT from that paper as I recall it, but I flag the exact recall as APPROXIMATE on fine details like specific latency percentiles quoted]**

**Problem:** In large fan-out, latency-sensitive request-serving systems (e.g., a search query fanning out to thousands of leaf servers), the overall response time is gated by the *slowest* responder (tail latency), and this tail grows with fan-out width even when the median leaf is fast.

**Method (FACT):** **Hedged requests**: send the same request to a second (or additional) replica if the first replica hasn't responded within some threshold (e.g., the 95th-percentile expected latency), and take whichever response comes back first, cancelling the other. A refinement noted in that line of work is **tied requests**, where the client marks both replicas as part of a tied pair so that whichever server starts executing first can proactively notify the other to abandon the request, reducing wasted work versus a client-side-only cancellation.

**Experimental environment (FACT):** Google-scale production request-serving systems (search-like fan-out architectures); the paper is written from a production-systems, not a single-benchmark-paper, perspective, so "experimental environment" is closer to "reported production behavior across systems" than one controlled experiment.

**Principal result (FACT):** Hedging even a small fraction of requests (the paper's point is that you don't need to hedge every request, just the ones already running long) substantially cuts high-percentile latency at a modest resource-cost overhead, because most hedged requests are cancelled quickly once the original responds.

**Limitations (FACT/OUR INTERPRETATION):** Hedging assumes requests are cheap relative to the value of latency reduction, and that the two replicas are *substitutable* (same request, same expected answer) — same substitutability assumption as MapReduce speculation, transplanted to RPC-style request/response instead of batch tasks. It also assumes low-cost, fast cancellation is available (killing the loser costs little).

**GhostRange relevance (OUR INTERPRETATION):** This is the cleanest transferable *trigger mechanism* for GhostRange: "start a second attempt if the first hasn't produced a signal within [threshold derived from the expected-latency distribution for this task_type], not on a fixed absolute timeout." It maps directly to reason code `STRAGGLER_DETECTED`. The *tied-request* refinement (loser proactively cancels itself when it learns it lost) is a concrete, cheap-to-implement cancellation-economics idea: if GhostRange forks a second world as a genuine duplicate-attempt hedge (case (a) above) and the first completes, the forked world's task should self-cancel via a scheduler-pushed cancellation signal rather than running to completion and being discarded after the fact — this recovers cost immediately instead of wasting the full remaining execution.

**What NOT to infer:** As with MapReduce, don't import the "take whichever finishes and discard the other" resolution rule wholesale for *hypothesis*-type speculation — only for infra-flakiness-driven duplicate speculation, where outputs really are substitutable.

**Implementation idea for GhostScheduler:** Compute a per-`task_type` expected-duration distribution from historical `estimated_duration` vs actual completion times (even a simple rolling p50/p90 is enough for v0); trigger `STRAGGLER_DETECTED` when a running task exceeds its task_type's p90 by a configurable multiplier (e.g., 1.5x), rather than a single global timeout — this is the direct GhostRange analog of hedging "already running long relative to peers," not an absolute deadline.

---

## 3. Branch prediction analogy (used carefully, as an *analogy*, not a system to cite)

**FACT/caveat:** Branch prediction (speculative instruction execution in CPU microarchitecture, e.g., the general lineage of work following Tomasulo-style out-of-order execution and later two-level adaptive predictors) is computer-architecture literature, not a distributed-systems paper — I'm treating it here explicitly as an **analogy**, not a citation to a specific systems paper relevant to cluster scheduling, since claiming a specific CPU branch-predictor paper as "GhostRange-relevant literature" would overstate the connection.

**OUR INTERPRETATION (the useful part of the analogy):** Three structural ideas transfer cleanly as *design vocabulary*, even though the mechanism doesn't:
1. **Speculate only when the predicted branch is worth it and misprediction is cheap to recover from.** CPUs speculate on nearly every branch because the *misprediction cost* (pipeline flush) is small relative to clock cycles saved when correct. GhostRange's misprediction cost (spinning up and then killing a whole cyber-world) is NOT small — this is the crucial disanalogy, and it's why GhostRange speculation must be far more selective than CPU branch prediction, gated by explicit cost/value checks rather than "speculate almost always."
2. **Confidence-gated speculation depth.** Modern predictors use confidence estimates to decide *how far* to speculate (e.g., how many predicted branches deep to keep executing before requiring confirmation). GhostRange analog: `uncertainty` on a task is a natural confidence-inverse signal — high `uncertainty` should gate *shallower* speculation (fork one alternative, wait for a signal before forking further), not deeper, because misprediction cost is asymmetric (real dollars) unlike a pipeline flush.
3. **Squash on misprediction must be cheap or the whole strategy is a net loss.** CPUs invest real transistor budget in making squash (rollback) fast. GhostRange's analog is explicit: cancellation must be a first-class, fast, low-cost operation in `execution-graph`/`range-runtime` (killing a world's compute + reclaiming its resources quickly) or speculative forking is a net negative regardless of how good the trigger heuristic is.

**What NOT to infer:** Do not cite "branch prediction" as if it were distributed-systems evidence about cluster behavior — it's included solely as a naming/design-vocabulary aid, and its quantitative results (e.g., predictor accuracy percentages) have zero applicability to cluster/world scheduling and should never be quoted as if relevant.

**Implementation idea for GhostScheduler:** Make cancellation cost an explicit, first-class field the scheduler can query per task_type/resource_profile (estimated teardown cost, akin to "squash cost"), and use it directly in the cancellation-economics formula below — this operationalizes point 3 rather than leaving it as prose.

---

## Concrete rules for GhostRange

### A. When to speculatively fork a second remediation candidate

Speculation should trigger when **all** of the following hold (each maps to a locked reason code or field):

1. `dependencies` are not blocking a second branch from starting (no `DEPENDENCY_CRITICAL` conflict — forking must not violate the DAG).
2. The first candidate's task has exceeded the straggler threshold for its `task_type` (see hedging rule above) **or** its live-updated `uncertainty` remains high past a checkpoint where it was expected to drop (a stalled-uncertainty signal, distinct from pure latency — a task can be "on time" but not reducing uncertainty, which is itself informative).
3. `estimated_cost` of forking a second candidate, discounted by `security_risk` and weighted by `expected_evidence_gain` of the *alternative* hypothesis, exceeds the marginal cost floor (see `ADAPTIVE_COMPUTE.md` stopping functions — speculation and stopping are two sides of the same value-of-information test, and should share one comparator function, not two separate ad hoc thresholds).
4. Budget headroom exists (not `BUDGET_EXHAUSTED`).

Concretely as a first-pass decision rule (v0, deterministic, explainable):

```
speculate_second_candidate(task) := 
    NOT dependency_conflict(task)
    AND (elapsed(task) > straggler_threshold(task.task_type)
         OR uncertainty_stalled(task))
    AND value_of_alternative_branch(task) > cost_of_fork(task) * risk_discount(task)
    AND NOT budget_exhausted()
```

Each boolean/term above should independently be attachable to a reason code when it flips the decision (e.g., `STRAGGLER_DETECTED` for the elapsed-time term, `HIGH_UNCERTAINTY` for the stalled-uncertainty term, `CHEAP_INFORMATION_GAIN` when the alternative branch is cheap-and-informative enough to justify forking, `BUDGET_EXHAUSTED` as a hard veto).

### B. Straggler detection specifics

- Use **relative** (peer-cohort, percentile-based) thresholds per `task_type`, not one global absolute timeout — directly per the hedged-request lesson. A `task_type` with naturally high variance (e.g., adversarial emulation runs that depend on attacker behavior) needs a wider threshold than a deterministic verification task_type.
- Track **two** straggler signals, not one: (1) elapsed-time-vs-peers (classic MapReduce/hedging signal), and (2) evidence-progress-vs-time (a task can be "on time" by elapsed-time but producing no incremental evidence — a subtler, more GhostRange-specific straggler mode that pure latency-based detectors like MapReduce's don't need, because MapReduce tasks don't have a partial-evidence-progress concept). Emit `STRAGGLER_DETECTED` on either signal, but record which signal fired, since the corrective action differs (case (a) infra retry vs. case (b) reconsidering whether this hypothesis branch is worth continuing at all, which shades into `MARGINAL_GAIN_LOW`/`BRANCH_LOW_VALUE` territory from `ADAPTIVE_COMPUTE.md`).

### C. Cancellation economics — when is killing a speculative branch worth it?

Define, for a running speculative task/world at decision time `t`:

- `sunk_cost(t)` = cost already spent (not recoverable — explicitly irrelevant to a rational forward-looking decision, included here only to name it and warn against the sunk-cost fallacy in implementation).
- `remaining_cost_to_completion` = estimated remaining `estimated_execution_cost` if allowed to finish.
- `cancellation_cost` = the "squash cost" from the branch-prediction analogy — actual overhead of tearing down the world/task cleanly (should be small and should be measured, per `range-runtime`; if it's not small, that's an architecture problem, not a scheduling one, and should be flagged back to Agent 07/11).
- `expected_remaining_evidence_gain` = the *live-updated* (Pollux-style, see `SCHEDULING.md` §5) estimate of how much additional evidence this branch is still expected to yield if allowed to finish, given everything observed about it so far (not its original static `expected_evidence_gain`).

**Kill the speculative branch when:**

```
expected_remaining_evidence_gain * security_risk * uncertainty_reduction  <  remaining_cost_to_completion + cancellation_cost
```

i.e., cancel when the *forward-looking* value of letting it finish (in the same units as the numerator of the priority formula, see `ADAPTIVE_COMPUTE.md` for the critique/redesign of that formula) is less than what it would cost to both finish it AND what it costs to stop it. Note the `cancellation_cost` term appearing on the *kill* side of the inequality is deliberate and important: if teardown is expensive, that raises the bar for killing, not lowers it — a branch worth almost-nothing but very expensive to tear down mid-flight might legitimately be let to finish rather than cancelled, which is a non-obvious and easy-to-get-backwards point implementers should be warned about explicitly.

**Do NOT kill merely because a sibling/duplicate finished first**, unless the branch is a case-(a) true-duplicate (MapReduce/hedging case) — for case-(b) hypothesis speculation, a sibling finishing first changes `expected_remaining_evidence_gain` (there may now be less unique value left, since some uncertainty was resolved by the sibling) but does not automatically zero it out; recompute the term, don't shortcut it.

---

## Explicit gaps / what I did not find high-confidence sources for

- I do not have confident specific-paper knowledge of speculative execution literature specifically for *adversarial security testing* or *cyber-range* contexts — I found none I can honestly cite, consistent with this being genuinely novel territory for GhostRange.
- I deliberately did not quote specific numeric results from "The Tail at Scale" or the MapReduce paper beyond qualitative claims, because I'm not fully certain of exact figures from memory and the project owner explicitly wants primary-source rigor over confident-sounding fabrication.
