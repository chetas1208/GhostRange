# Adaptive Compute & Stopping-Decision Research for GhostScheduler v0

Owner: Agent 10 (Adaptive Compute Researcher). Status: research complete for M1, feeds `packages/scheduler` and `packages/execution-graph`. This document is the most implementation-facing of the three research deliverables: Section 3 gives concrete, directly codable stopping functions, and Section 4 gives a concrete critique + replacement of the candidate priority formula.

---

## 1. Literature: test-time compute scaling, value-of-information, bandits

### 1.1 Test-time / inference-time compute scaling (recent LLM literature)

**FACT (general, [APPROXIMATE] on specific paper attribution):** There is a body of 2023-2024 work showing that for LLM reasoning tasks, allocating more inference-time compute (more sampled reasoning chains, longer chain-of-thought, more revision/verification passes) can improve answer quality up to a point, and that *how* the extra compute is spent (more samples vs. longer single chains vs. verifier-guided search) matters more than raw compute quantity — this is often discussed under headings like "test-time compute scaling" or "inference-time scaling laws." I recall this as a real and active research area (with work from groups studying scaling of sampling strategies, best-of-N with verifiers, and tree-search-guided generation) but I do **not** have confident, citation-level recall of specific paper titles/authors/venues I could state as verified fact without risk of misattribution, so I am deliberately not naming specific titles here. Treat this sub-section as **[APPROXIMATE / GENERAL KNOWLEDGE, not a citable reference]**.

**OUR INTERPRETATION:** The qualitative lesson that *does* transfer regardless of exact citation: compute allocated to "thinking longer" has **diminishing and eventually near-zero marginal returns**, and the right response is not a fixed compute budget per query but a *value-of-information-gated* stopping rule — keep spending only while the marginal expected quality gain per unit compute clears a bar. This is structurally identical to GhostRange's problem: keep a branch running only while marginal expected evidence gain per unit cost clears a bar.

**GhostRange relevance:** This is the direct intellectual ancestor of `MARGINAL_GAIN_LOW`. The "verifier-guided" variant (spend compute on a cheap checker to decide whether to spend more compute on generation) is a useful analogy for a scheduler that itself needs to be cheap relative to what it's scheduling — the *scheduling decision* about whether to keep a branch alive should be far cheaper than the branch's own execution cost, mirroring how a verifier is meant to be cheaper than another full generation.

### 1.2 Value-of-information (VoI) and Bayesian sequential experimental design

**FACT (general knowledge, decision theory / statistics, not one paper):** Classical decision theory defines the *expected value of (perfect/sample) information* as the expected improvement in decision quality from acquiring more data before committing to a decision, net of the cost of acquiring it. Sequential/Bayesian experimental design formalizes "should I run one more experiment" as: keep sampling while `E[value of updated belief after next sample] - E[value of current belief] > cost of next sample`. **[This is standard decision-theory framing, not attributed to a single citable paper — treat as textbook-level general knowledge.]**

**OUR INTERPRETATION:** This is the *exact* mathematical shape GhostRange needs for a stopping rule, and it should be treated as more foundational than any single ML systems paper: `uncertainty_reduction` in the locked Task schema is implicitly a VoI proxy, and the stopping decision should be framed explicitly as "expected marginal reduction in decision-relevant uncertainty, per unit cost, compared to a floor" — not as an ad hoc heuristic invented from scratch.

**GhostRange relevance:** VoI gives us the correct *units* discipline that the naive priority formula (critiqued in Section 4) currently lacks — value-of-information is a single scalar with a defensible unit (uncertainty-reduction, or equivalently decision-quality-improvement), and cost has an unambiguous unit (dollars or compute-seconds); a good formula divides one by the other and compares to a floor, rather than multiplying five heterogeneous factors together.

### 1.3 Multi-armed bandits (uncertainty-aware allocation)

**FACT (general knowledge, classical + well-known algorithms):** The multi-armed bandit framing allocates limited trials across competing options ("arms") to maximize cumulative reward or identify the best arm, under uncertainty about each arm's true payoff. Two families are relevant:
- **UCB (Upper Confidence Bound) family** (Auer, Cesa-Bianchi, Fischer and related lineage, **[APPROXIMATE attribution]**): pick the arm with the highest "optimistic" estimate (mean reward + confidence bonus that shrinks as more samples are taken of that arm), naturally balancing exploration (try uncertain arms) and exploitation (favor arms known to be good).
- **Thompson Sampling** (originally Thompson, 1933, **[APPROXIMATE — I recall this is a very old paper predating modern bandit literature by decades, revived in the 2000s-2010s; exact revival citation not confident]**): maintain a posterior belief over each arm's true payoff, sample from each posterior, play the arm with the best sample — probabilistically explores in proportion to genuine uncertainty.

**OUR INTERPRETATION:** GhostRange's "which branch/world to allocate the next unit of compute to" is structurally a **best-arm-identification bandit problem with heterogeneous, unequal, and expensive pulls** (each "pull" is not a cheap slot-machine trial, it's a costly compute allocation with side effects), which is a harder variant than the textbook bandit setting (textbook bandits generally assume pulls are cheap/uniform-cost; GhostRange's pulls have a `estimated_execution_cost` that varies per arm and per pull).

**GhostRange relevance:** The `security_risk` and `dependency_criticality` factors in the priority formula function like a *prior bias* term on top of the bandit's usual explore/exploit balance — a branch can be worth prioritizing not because its posterior mean evidence-gain is highest (pure bandit logic) but because its downstream dependency/risk profile makes information about it categorically more valuable regardless of the bandit-optimal exploration schedule. This is a genuine GhostRange-specific wrinkle beyond plain bandit theory: **GhostScheduler is a bandit problem overlaid with a risk/dependency prior that the bandit literature doesn't natively model.**

**What NOT to infer:** Full bandit algorithms (UCB, Thompson Sampling) are explicitly **learned/adaptive-statistics** approaches that update posteriors from reward observations over many trials — this is close to (though not identical to) the "reinforcement learning" category Decisions.md explicitly says GhostScheduler v0 must NOT be. Do not implement UCB/Thompson Sampling as the v0 mechanism. However, per Decisions.md's explicit instruction that v0 should be "designed so learned policies could replace/augment heuristics later," the stopping functions below are deliberately structured so that a future bandit-posterior estimate could be substituted in for the deterministic point-estimate of `expected_evidence_gain` without changing the surrounding formula shape — see Section 3.4.

---

## 2. What makes a stopping decision "GhostRange-shaped" rather than generic

Before giving formulas, the key structural facts that distinguish this from a textbook stopping problem:

1. **Costs are not sunk-cost-symmetric.** Money already spent on a branch is irrelevant to whether to continue (classic sunk-cost-fallacy warning) — but *cancellation itself has a cost* (see `SPECULATION.md` §C), so the decision is not simply "continue vs. free stop," it's "continue vs. pay to stop."
2. **Evidence gain is not i.i.d. across time.** Early samples/checks in a branch usually resolve more uncertainty than later ones (diminishing returns is the *expected* shape, not an edge case) — stopping functions should assume a concave (diminishing-returns) evidence-accumulation curve by default, and treat a branch that's *not* showing diminishing returns as an anomaly worth a reason code of its own, not the null hypothesis.
3. **Multiple currencies must be reconciled**: dollars (execution cost), risk (security exposure), and information (uncertainty reduction) are different units. Any formula that naively multiplies or adds across these without normalization is a units bug, not just a stylistic weakness (this is the core critique in Section 4).
4. **Explainability is a hard constraint**, not a nice-to-have — a stopping/continuation decision must resolve to one or more of the ten locked reason codes. A stopping function that can't be decomposed into "which term caused this" is not acceptable for v0 regardless of its statistical elegance.

---

## 3. Concrete candidate stopping functions

These are meant to be directly usable by the `execution-graph`/`scheduler` implementers. All three share the same three inputs computed per task/branch at each scheduler tick:

- `g_hat(t)` — current point estimate of **remaining** expected evidence gain if the branch continues (NOT the original static `expected_evidence_gain` — must be live-updated per the Pollux-style re-estimation argument in `SCHEDULING.md` §5).
- `c_hat(t)` — estimated **remaining** cost to get that gain (not total cost so far — sunk cost excluded by construction).
- `risk(t)`, `dep(t)` — current `security_risk` and `dependency_criticality` values (assumed normalized to comparable [0,1]-ish ranges; see Section 4 for why this normalization must be enforced upstream, not assumed for free).

### 3.1 Function A — Marginal Value-of-Information Ratio with Floor (recommended default for v0)

```
marginal_ratio(t) = (g_hat(t) * risk(t) * dep(t)) / max(c_hat(t), c_min)

STOP if marginal_ratio(t) < floor_threshold
```

- `c_min` is a small floor cost to avoid division blow-up when remaining estimated cost is near zero (a task that's nearly free to continue should not produce an artificially huge ratio from a near-zero denominator — cap the *benefit* of cheapness, don't let it go unbounded).
- `floor_threshold` is a single tunable knob, ideally expressed as "minimum acceptable evidence-per-dollar," calibrated against the operator's overall budget (e.g., derived from `BUDGET_EXHAUSTED` headroom — as budget gets scarcer, `floor_threshold` should rise, making the scheduler pickier automatically. This is a concrete, deterministic link between budget state and stopping behavior, which the naive multiplicative priority formula has no mechanism for at all.).
- **Reason code mapping:** fires `MARGINAL_GAIN_LOW` when `g_hat(t)` is the dominant reason the ratio is low; fires `CHEAP_INFORMATION_GAIN` as the *inverse* signal (used to justify *continuing* or even accelerating, not stopping) when the ratio is high because `c_hat(t)` is unusually low, not because `g_hat` is high — worth logging which side of the ratio moved, for explainability.
- **Why this is the recommended default:** it directly operationalizes the VoI framing from Section 1.2 with the fewest moving parts, requires no probability distributions or posteriors (satisfying the "not RL, transparent, deterministic" requirement), and every term is independently inspectable for the reason-code output.

### 3.2 Function B — Diminishing-Returns Slope Detector (complementary trigger, not a replacement)

Rather than a ratio against a fixed floor, track the *trend* of evidence accumulation directly:

```
slope(t) = (evidence_accumulated(t) - evidence_accumulated(t - Δ)) / cost_spent(t) - cost_spent(t - Δ))

STOP if slope(t) < slope_floor  AND  elapsed(t) > min_observation_window
```

- This answers a different question than Function A: not "is the ratio of remaining-estimated value to remaining-estimated cost too low" (which depends on an *estimate* of the future) but "has the *observed, realized* rate of evidence production over the last window actually stalled" (which depends only on measured history, no forecasting). The two are complementary: Function A can misfire on a noisy single-point estimate of `g_hat`, whereas Function B is robust to estimation error because it only looks backward at what actually happened, at the cost of reacting slower (needs `min_observation_window` of data before it can trigger, so it's blind at the very start of a branch).
- `min_observation_window` is essential — without it, a branch that simply hasn't produced its first piece of evidence yet (but is about to) would be killed prematurely; this directly encodes the "diminishing returns is the expected default shape but early-branch behavior is a special case" point from Section 2.2.
- **Reason code mapping:** `MARGINAL_GAIN_LOW` (same as Function A, but triggered on realized history rather than forecast) when slope has stalled; combine with `STRAGGLER_DETECTED` when slope stalling coincides with elapsed-time-vs-peers being high (see `SPECULATION.md` §B) — these are related but distinct signals and both should be loggable independently even when they co-fire, since a future learned policy (per the "designed so learned policies could augment heuristics later" requirement) may want to weight them differently.
- **Recommended usage:** run Function A and Function B together; either firing is sufficient to flag a branch as a stop candidate, but a branch should only be *actually killed* (vs. just flagged/deprioritized) when combined with the cancellation-economics check from `SPECULATION.md` §C, since flagging low marginal value and actually paying to tear down are different decisions.

### 3.3 Function C — Budget-Conditioned Dependency-Weighted Threshold (handles `dependency_criticality` and `BUDGET_EXHAUSTED` explicitly)

A branch that's individually low-value can still be worth continuing if it's a hard dependency for a high-value downstream branch (this is what `DEPENDENCY_CRITICAL` is for, and neither Function A nor B accounts for downstream dependents by default — they only look at *this* branch's own evidence/cost). Function C is a **veto/override layer**, applied after A/B produce a stop recommendation:

```
effective_stop = (Function_A_says_stop OR Function_B_says_stop)
                  AND NOT (dep(t) >= dependency_critical_threshold AND downstream_blocked_without(t))
                  AND NOT budget_exhausted_override(t)

budget_exhausted_override(t) = TRUE  when total_spend >= hard_budget_cap
   (this override FORCES stop regardless of A/B/dependency, i.e. BUDGET_EXHAUSTED trumps DEPENDENCY_CRITICAL)
```

- `downstream_blocked_without(t)` is a boolean derived directly from the `dependencies` DAG (does any pending/active task list this one as a dependency with no viable alternative path) — this is a graph query into `execution-graph`, not a statistical estimate, and should be exact/deterministic.
- **Explicit precedence rule (important, and easy to implement backwards):** `BUDGET_EXHAUSTED` is a hard ceiling that overrides even `DEPENDENCY_CRITICAL` — a dependency being critical doesn't create money that doesn't exist. This precedence should be encoded explicitly in code (e.g., an ordered reason-code evaluation list) rather than left implicit in whatever order conditions happen to be checked, because silent implicit ordering is exactly the kind of thing that breaks explainability later.
- **Reason code mapping:** `DEPENDENCY_CRITICAL` (override triggered), `BUDGET_EXHAUSTED` (hard override, highest precedence).

### 3.4 Forward-compatibility note (for the "learned policy later" requirement)

All three functions above consume `g_hat(t)` as a **point estimate**. To make room for a future learned/bandit-posterior policy without restructuring the scheduler:
- Define `g_hat(t)` behind a single interface (e.g., an `EvidenceGainEstimator` with a `.estimate(task, history) -> float` method) that v0 implements as a simple heuristic (e.g., exponentially-weighted moving average of recently observed evidence deltas for that `task_type`), so a later version can implement the same interface with a bandit posterior mean or a learned model **without changing Functions A/B/C themselves** — the stopping-function shape (ratio-with-floor, slope-detector, dependency-veto) stays fixed and deterministic/explainable; only the *estimator feeding it* becomes learned. This is the concrete mechanism for satisfying "not RL initially, but designed so learned policies could replace/augment heuristics later."

---

## 4. Critique of the candidate priority formula

Candidate formula (given, explicitly not sacred):

```
priority = expected_evidence_gain * security_risk * uncertainty_reduction * dependency_criticality / estimated_execution_cost
```

### 4.1 What's wrong with it (concrete, not just "it's naive")

1. **Units mismatch across the four numerator factors.** `expected_evidence_gain` and `uncertainty_reduction` are information-theoretic-ish quantities (plausibly bounded, e.g., [0,1] if normalized as a fraction of total uncertainty resolved); `security_risk` and `dependency_criticality` are categorical-severity-ish quantities with no natural information-theoretic unit at all. Multiplying four differently-typed quantities together produces a number with no defensible unit, which makes `floor_threshold`-style comparisons (needed for any stopping rule, see Section 3) meaningless — you cannot set a sensible global floor on a quantity whose unit changes depending on which factor happens to dominate.
2. **Zero-collapse (any single 0 kills the whole score).** Since all four numerator terms are multiplied, if any *one* of them is legitimately at or near 0 (e.g., a task with currently-zero measured `security_risk` because the vulnerable component simply hasn't been reached yet, not because it's actually safe), the entire priority collapses to 0 regardless of how large the other three factors are. This is almost certainly not intended — a task with enormous `expected_evidence_gain` and `dependency_criticality` should not be treated as *literally worthless* just because one factor is temporarily unmeasured/zero. Multiplicative structure is the wrong shape whenever any factor can legitimately be zero or near-zero as a normal (not error) state.
3. **Unbounded blowup from the denominator.** `estimated_execution_cost` in the denominator means priority is unbounded as cost approaches zero — a nearly-free task with modest evidence gain would dominate the entire schedule over a hugely informative but moderately expensive task, purely from a denominator artifact, not because it's actually the better use of the next dollar. This needs an explicit floor (`c_min`, as in Function A above) at minimum, and arguably a different structure entirely (see 4.3).
4. **No normalization contract stated for any factor.** Nothing in the locked field list specifies that `security_risk`, `uncertainty_reduction`, `dependency_criticality` are guaranteed to be in the same numeric range (e.g., all [0,1], or all same scale of "criticality points"). Without an explicit normalization contract enforced at the contract/schema layer (packages/contracts), any formula — this one or its replacement — is unreliable, because whichever factor happens to have the widest numeric range will silently dominate priority ordering regardless of its actual importance. **This is arguably the single most urgent, cheapest-to-fix issue**, independent of which formula is chosen.
5. **No treatment of diminishing returns / time-dependence.** The formula as given is a single static snapshot value; it has no notion that `expected_evidence_gain` should be *re-estimated* as the task runs (per the Pollux/goodput argument in `SCHEDULING.md` §5) — used as a one-shot ranking at task creation, it can't drive an ongoing stop/continue decision at all, which is the actual operational need.
6. **No explicit place for budget state.** Nothing in the formula reacts to remaining budget — `BUDGET_EXHAUSTED` has to be bolted on as a separate out-of-band check rather than being a natural term/threshold-modifier in the formula itself (Function A above fixes this by making the floor threshold budget-conditioned).

### 4.2 What NOT to do in "fixing" it

- Don't just add small epsilons to prevent zero-collapse/division blowup and call it fixed — that treats the symptom (numerical edge case) without treating the actual problem (wrong structural shape for factors that can legitimately be zero, and no normalization contract).
- Don't jump to a black-box learned weighting (e.g., "just fit weights via regression on outcomes") — that violates the explicit "not RL initially, transparent, deterministic" requirement and there is no outcome-labeled training data yet in M1 anyway.

### 4.3 Proposed v0 replacement structure

**Design decision (OUR DESIGN DECISION, explicitly proposed for ADR, not silently substituted):** Replace naive multiplication with a **normalized weighted log-sum for the value terms, kept separate from a ratio-with-floor against cost**, plus explicit additive (not multiplicative) treatment of risk/dependency as *priority boosts* rather than multiplicative collapse-risks:

```
# Step 1: normalize every factor to [0,1] at the contracts layer (packages/contracts),
# enforced by validation, not assumed by convention.
# (This is the single highest-priority fix regardless of formula choice.)

# Step 2: value_score combines evidence gain and uncertainty reduction
#          via a weighted LOG-SUM (not product), which avoids zero-collapse:
#          log(1+x) keeps the term finite and well-behaved near 0, and
#          summing (not multiplying) means one weak factor doesn't zero out a strong one.
value_score = w1 * log(1 + expected_evidence_gain) + w2 * log(1 + uncertainty_reduction)

# Step 3: risk and dependency act as ADDITIVE boosts (a bonus for mattering more),
#          not multiplicative collapse-risks — expressed as a bounded boost factor:
boost = 1 + w3 * security_risk + w4 * dependency_criticality
        (all terms already normalized to [0,1]; w3, w4 tunable, e.g. start at 0.5 each,
         so max boost is a 2x multiplier, not unbounded)

# Step 4: combine value and boost, THEN divide by cost with an explicit floor:
priority = (value_score * boost) / max(estimated_execution_cost, cost_floor)
```

**Why this addresses each critique:**
- Zero-collapse (4.1.2) fixed: `log(1+x)` and additive-sum structure mean a single 0 factor reduces but does not annihilate the score; `boost` has a floor of 1 (no risk/dependency contribution at all still leaves `boost = 1`, i.e., neutral, not a penalty).
- Unbounded blowup (4.1.3) fixed: explicit `cost_floor` in the denominator, same fix as Function A in Section 3.
- Units mismatch (4.1.1) fixed *conditionally*: still requires Step 1 (contract-level normalization) to actually be enforced — this formula does not solve the units problem by itself, it only becomes valid once every input is guaranteed [0,1]. This dependency should be called out explicitly to the contracts/schema owner (Agent 14 / packages/contracts) as a hard requirement, not an implementation detail left to each producer of these fields.
- No normalization contract (4.1.4): explicitly flagged as Step 1, a prerequisite, not an afterthought — **recommend this becomes a Pydantic validator (`@field_validator`) in packages/contracts constraining these four fields to `[0.0, 1.0]` at the schema level**, so it's structurally impossible for a producer to emit an out-of-range value rather than relying on convention.
- Diminishing returns / time dependence (4.1.5): not solved by the formula shape itself — this is handled by re-invoking the formula on a live-updated `expected_evidence_gain`/`uncertainty_reduction` per tick (Section 1.1/3.4), which should be documented as a *usage contract* for this formula ("recompute at every scheduler tick using current estimates, not just at task creation") alongside the formula itself.
- Budget state (4.1.6): still requires the Function A/C treatment layered on top (budget-conditioned floor threshold, `BUDGET_EXHAUSTED` hard override) — this replacement formula produces a better-behaved *priority score*, but the *stop/continue decision* is a separate downstream comparison against the stopping functions in Section 3, not something the priority formula alone should try to encode.

**Alternative considered and explicitly rejected for v0:** A pure ratio-of-sums structure (e.g., `(a+b+c+d)/cost` with no log/boost distinction) was considered simpler, but rejected because it treats risk/dependency as freely fungible with evidence-gain/uncertainty-reduction (i.e., enough `dependency_criticality` could compensate for literally zero `expected_evidence_gain`, which seems wrong — a task that resolves nothing shouldn't be scheduled just because it's "critical" in the abstract, dependency criticality should *boost* genuinely valuable work, not manufacture value from nothing). The log-sum-then-boost structure keeps this distinction explicit and inspectable, which also directly serves the reason-code requirement: `value_score` maps cleanly to `HIGH_UNCERTAINTY`/`CHEAP_INFORMATION_GAIN`-type codes, `boost` maps cleanly to `HIGH_ASSET_RISK`/`DEPENDENCY_CRITICAL`-type codes, and they're separable terms an explanation can cite independently — exactly the property the naive product formula lacked.

---

## 5. Summary of concrete deliverables in this document (for implementers)

1. Three stopping functions (A: ratio-with-floor, B: slope detector, C: dependency/budget veto layer) with pseudocode, ready to implement in `packages/scheduler`.
2. An explicit forward-compatible estimator interface pattern (Section 3.4) so v0's heuristic estimate of `expected_evidence_gain` can later be swapped for a learned/bandit posterior without restructuring the scheduler.
3. A concrete, itemized critique of the given priority formula (six distinct issues, not vague hand-waving) plus a replacement formula (log-sum value score × bounded additive boost ÷ cost-with-floor) with an explicit, callable-out dependency on a contracts-layer normalization requirement that must be raised with Agent 14/packages/contracts.

## Explicit gaps / what I did not find high-confidence sources for

- Section 1.1 (test-time compute scaling) is presented as general/approximate knowledge rather than citable fact, since I cannot confidently name specific papers/authors/venues for this fast-moving area without risking fabrication.
- I did not find (nor would expect to find) any existing literature directly addressing "stopping rules for adversarial cyber-remediation verification branches" — this confirms the problem GhostScheduler is solving is genuinely novel, and the proposed functions in Section 3 are original synthesis (OUR DESIGN DECISION) built from adjacent, better-established literature (VoI theory, bandits, diminishing-returns detection), not a transcription of an existing system.
