# Scheduling Research for GhostScheduler v0

Owner: Agent 08 (Scheduler Researcher). Status: research complete for M1, feeds `packages/scheduler` and `packages/execution-graph` design.

## Purpose and scope

GhostScheduler decides what compute runs where, concurrently with what, for how long, and whether the next dollar of compute is worth spending — across *investigation branches* (forked remediation-candidate "cyber worlds"), not generic batch jobs. This document surveys heterogeneous CPU/GPU cluster scheduling literature I have genuine knowledge of, and for each source separates **FACT** (what the paper showed), **OUR INTERPRETATION** (how we read it), and **OUR DESIGN DECISION** (what we're doing about it). Where my recollection of a specific numeric result, venue/year, or author list is not fully certain, it is flagged **[APPROXIMATE]** rather than stated as verified fact. I have not fabricated papers I don't recall — several plausible topics (e.g., a named "LLM-serving scheduler" system, specific fragmentation papers) are covered at the level of general knowledge/pattern rather than pretending citation-level certainty, and are marked as such.

---

## 1. Sparrow — decentralized low-latency task scheduling

**Citation:** Ousterhout, K., Wendell, P., Zaharia, M., Stoica, I. "Sparrow: Distributed, Low Latency Scheduling." SOSP 2013. **[APPROXIMATE on exact page/proceedings numbers, confident on venue/year/authors/core mechanism]**

**Problem:** Centralized schedulers become a throughput/latency bottleneck when task scheduling decisions must happen in milliseconds at the scale of hundreds of thousands of short tasks per second (e.g., short interactive-query workloads on large clusters).

**Method (FACT):** Sparrow uses *batch sampling* and *power of two choices*-style randomized load balancing: for a job with multiple tasks, it probes a small number of random worker queues (more than the number of tasks needed) and places tasks on whichever probed workers report the shortest queue, without global state. It adds *late binding* — a worker only commits to running a probed task when it actually reaches the front of its queue and confirms the task is still unclaimed — to avoid two schedulers racing onto the same idle slot.

**Experimental environment (FACT):** Simulated and real deployment on a cluster (order ~100 nodes in the paper's real deployment, larger via simulation), workload modeled on Facebook/Hive-style short analytic queries; task durations in the ~milliseconds-to-seconds range.

**Principal result (FACT):** Near-optimal task placement (within a small constant factor of an omniscient centralized scheduler) at a small fraction of the scheduling latency, and scheduler throughput scales horizontally because there's no single decision point.

**Limitations (FACT/OUR INTERPRETATION):** Sparrow assumes tasks are roughly homogeneous in resource shape and short-lived; it has weak support for placement constraints, fairness across users, and heterogeneous resource types (no GPU-era resource packing). It's a *queueing* scheduler, not a *value-of-information* scheduler — it doesn't know or care whether one task's output is more informative than another's.

**GhostRange relevance (OUR INTERPRETATION):** GhostRange tasks are NOT homogeneous short probes — they're heterogeneous, priority-weighted investigation steps with real cost. Sparrow's core idea we *can* reuse is the decentralization pattern for a specific narrow case: cheap, frequent, low-stakes scheduling decisions (e.g., dispatching many small verification probes across worker pool) shouldn't all route through one heavyweight priority-recomputation pass.

**What NOT to infer:** Do not infer that decentralized/randomized placement is appropriate for GhostScheduler's top-level branch/task priority decisions — those are explicitly meant to be deterministic and explainable per Decisions.md, and Sparrow's randomization is antithetical to reason-coded explainability. Sparrow also says nothing about cost-awareness or cancellation economics.

**Implementation idea for GhostScheduler:** For the *low-level dispatch* layer only (assigning an already-prioritized task to one of several idle homogeneous-enough workers), use a bounded "probe N of M idle workers, pick least-loaded, late-bind" mechanism instead of full central bookkeeping of every worker's exact queue depth — this keeps the hot dispatch path cheap while keeping the *priority computation* (which produces the reason codes) fully centralized and deterministic upstream.

---

## 2. Tetris — multi-resource packing via clustering / heterogeneity scoring

**Citation:** Grandl, R., Ananthanarayanan, G., Kandula, S., Rao, S., Akella, A. "Multi-Resource Packing for Cluster Schedulers." SIGCOMM 2014. **[APPROXIMATE on venue — I recall this as SIGCOMM 2014, but am not fully certain vs. a co-located workshop; authors/core idea are solid]**

**Problem:** Cluster jobs have multi-dimensional resource demands (CPU, memory, disk I/O, network) that don't reduce to one scalar; naive schedulers that optimize one dimension (or use dominant-resource fairness alone) leave other resources fragmented/underutilized.

**Method (FACT):** Tetris scores candidate task-to-machine placements using a **dot-product-like "alignment" score** between a task's resource-demand vector and a machine's available-resource vector — favoring placements that pack complementary shapes together (a CPU-heavy task next to a memory-heavy one on the same box) analogous to fitting Tetris pieces. It also incorporates a preference for tasks nearer their dependents (heuristic locality) to reduce data-movement cost, using a scoring function that trades off packing efficiency against completion-time impact.

**Experimental environment (FACT):** Trace-driven simulation and a real deployment on a cluster running mixed batch workloads (Hadoop/Spark-like DAG jobs); resource dimensions include CPU, memory, disk, network.

**Principal result (FACT):** Improved makespan and multi-resource utilization (tens of percent range) over schedulers optimizing a single resource dimension or classic fair-share alone, without significantly hurting fairness.

**Limitations (FACT/OUR INTERPRETATION):** The scoring heuristic is a greedy local decision at each scheduling event, not globally optimal; it needs reasonably accurate resource-demand estimates per task, which are often just historical averages/profiles, not one true value.

**GhostRange relevance (OUR INTERPRETATION):** Directly relevant to the `resource_profile` field on the locked Task contract. When GhostScheduler must place multiple concurrent world/task combos onto a fixed worker fleet (mixed CPU/GPU/memory shapes), a Tetris-style alignment score between `resource_profile` and remaining node capacity is a concrete, explainable, deterministic packing rule — and "why did task X wait" can literally cite the alignment score, satisfying the reason-code requirement.

**What NOT to infer:** Tetris optimizes throughput/packing, not evidentiary value — it has zero concept of "is this task worth running at all," which is GhostScheduler's actual novel problem. Don't treat Tetris's score as a substitute for the `priority` field; it's a placement-time tiebreaker among already-approved tasks, not a decision of *whether* to run something.

**Implementation idea for GhostScheduler:** Add a `PLACEMENT_SCORE` (implementation detail, not one of the locked reason codes, but a diagnostic sub-score) computed as normalized dot product of `resource_profile` demand vector vs. each candidate node's free-capacity vector; use it strictly for *node selection among already-scheduled tasks*, after `priority`/reason-code eligibility has already gated *whether* the task runs.

---

## 3. Gandiva — GPU cluster scheduling for deep learning with introspection

**Citation:** Xiao, W., Bhardwaj, R., Ramjee, R., Sivathanu, M., Kim, N., Kwon, F., Zhang, X., Karampatziakis, N., Xu, S., Yang, F. "Gandiva: Introspective Cluster Scheduling for Deep Learning." OSDI 2018. **[Reasonably confident on venue/year/core mechanism, less confident on complete/exact author list]**

**Problem:** Deep learning training jobs are long-running, have highly variable and hard-to-predict-upfront resource efficiency (a job's ideal batch size/GPU count isn't known before running), and naive time-slicing or static allocation wastes GPU time.

**Method (FACT):** Gandiva introduces **introspective scheduling**: it monitors a running job's actual GPU utilization/efficiency at runtime and dynamically migrates, time-slices, or grows/shrinks the job's allocation based on observed behavior rather than an upfront static estimate. It exploits intra-job iteration boundaries (checkpoint-friendly points) to migrate jobs between GPUs cheaply, and packs multiple jobs onto one GPU via time-slicing when a job doesn't need the whole device.

**Experimental environment (FACT):** Real GPU cluster (multi-GPU servers, e.g., machines with several GPUs each) running deep learning training jobs (image classification / RNN-style workloads typical of that era's DL scheduling papers).

**Principal result (FACT):** Significant improvement in cluster-wide GPU utilization and job completion time versus static/first-fit GPU allocation, by adapting allocation live rather than trusting the job's initial resource request.

**Limitations (FACT/OUR INTERPRETATION):** Requires checkpoint/migration support in the job runtime (deep-learning-framework-specific); the introspection signal (GPU utilization %) is a good proxy for DL training but is not a general "is this job producing value" signal — a GPU can be 100% utilized on a computation that yields no new evidence.

**GhostRange relevance (OUR INTERPRETATION):** Directly informs the `GPU_ACCELERATION_EXPECTED` / `GPU_NOT_JUSTIFIED` reason codes. Gandiva's core lesson — *don't trust a static upfront resource claim, measure actual utilization and reallocate* — maps to: don't trust a task's declared `resource_profile` GPU need blindly; if a GPU-flagged remediation-verification task is observed at low GPU utilization shortly after start, that is exactly the evidence needed to emit `GPU_NOT_JUSTIFIED` and reclaim the device for another world.

**What NOT to infer:** Don't infer that GhostRange tasks are migratable/checkpointable at the granularity Gandiva assumes (arbitrary DL training loops) — CALDERA-driven adversarial re-verification workloads are more likely opaque black boxes from the scheduler's point of view (a subprocess/container running attack emulation), so live migration may not be safely implementable in M1; treat Gandiva's *diagnostic signal* (utilization introspection) as adoptable now, its *live migration mechanism* as a stretch goal, not a v0 assumption.

**Implementation idea for GhostScheduler:** Implement a lightweight GPU-utilization sampler per running task; if a task declared GPU resource need but shows utilization below a threshold (e.g., <15%) for more than N seconds after warmup, emit reason code `GPU_NOT_JUSTIFIED` and demote/reclaim the GPU allocation for that task going forward (kill+respawn on CPU-only profile, or deprioritize for the node's GPU slot).

---

## 4. Themis — fairness for ML workloads via a game-theoretic finish-time metric

**Citation:** Mahajan, K., Balasubramanian, A., Singhvi, A., Venkataraman, S., Akella, A., Phanishayee, A., Chowdhury, M. "Themis: Fair and Efficient GPU Cluster Scheduling." NSDI 2020. **[Reasonably confident on venue/year; moderately confident on full author list]**

**Problem:** Fair-share schedulers for ML training (e.g., dominant resource fairness) don't account for the fact that different jobs get *different marginal benefit* from the same resource allocation over time, leading to allocations that are "fair" by a static resource metric but unfair in actual completion-time impact.

**Method (FACT):** Themis defines a **finish-time fairness** metric — comparing a job's actual completion time under shared allocation to its hypothetical completion time if it had an equal fair share for its entire life — and uses a decentralized, auction-like mechanism where jobs bid for resources based on how much a given allocation would improve their finish-time fairness metric, arbitrated in a way designed to resist gaming.

**Experimental environment (FACT):** Simulation plus real cluster deployment running representative ML training jobs of varying size/duration on shared GPU clusters.

**Principal result (FACT):** Improved fairness (in the finish-time sense) and lower average completion time compared to classical fair-share and utilitarian-throughput-optimizing baselines, without a central omniscient allocator.

**Limitations (FACT/OUR INTERPRETATION):** The fairness definition is specifically about *tenants/jobs getting their fair long-run share*, which presumes symmetric users worth treating equally — GhostRange doesn't have "tenants" in that sense, it has investigation branches of *asymmetric, explicitly unequal* importance (a high-risk branch should legitimately starve a low-risk one, not be "fair" to it).

**GhostRange relevance (OUR INTERPRETATION):** Directly relevant to reason code `BRANCH_LOW_VALUE` and the general principle that GhostScheduler should be intentionally *unfair* across branches proportional to evidentiary value, which is the opposite design point from Themis. Still, Themis's core technique — measure a normalized "how much is this allocation actually helping vs. a baseline" ratio — is reusable as the mathematical shape of a *within-branch* fairness check (e.g., across parallel tasks racing inside the same world, so one hypothesis doesn't starve a sibling hypothesis for no evidentiary reason).

**What NOT to infer:** Do not adopt Themis's cross-tenant fairness as a top-level goal for GhostScheduler — deliberately unequal allocation across branches by evidentiary value is the point, not a bug to fix. Don't infer the auction/bidding mechanism is appropriate for M1's deterministic-and-explainable requirement — an auction's outcome is harder to reduce to a single reason code than a direct formula.

**Implementation idea for GhostScheduler:** Borrow the *ratio* framing, not the auction: define a per-branch "starvation ratio" = actual compute received / compute it would receive under equal per-branch split, and use it only as a *guardrail* (if a branch's ratio drops below a floor while its `priority` is not being emitted as `BRANCH_LOW_VALUE`, that's a scheduler bug/starvation signal worth logging, not something to auto-correct against the priority ordering).

---

## 5. Pollux — goodput-aware adaptive resource allocation for DL training

**Citation:** Qiao, A., Choe, S.K., Subramanya, S.J., Neiswanger, W., Ho, Q., Zhang, H., Ganger, G., Xing, E. "Pollux: Co-adaptive Cluster Scheduling for Goodput-Optimized Deep Learning." OSDI 2021. **[Reasonably confident on venue/year/core "goodput" concept; moderate confidence on complete author list]**

**Problem:** Static resource allocation for DL training ignores that a job's *statistical efficiency* (progress per training step) and *system throughput* (steps per second) both change with batch size and resource allocation, and jointly co-adapting both is better than optimizing either alone.

**Method (FACT):** Pollux defines **goodput** = system throughput × statistical efficiency, and continuously re-tunes both a job's training hyperparameters (e.g., batch size) and its cluster resource allocation (number of GPUs) to maximize goodput cluster-wide, using online profiling of each job's throughput/efficiency curves rather than a static upfront model.

**Experimental environment (FACT):** Real GPU cluster running mixed DL training jobs of different model families, compared against allocation-only schedulers that don't co-adapt batch size.

**Principal result (FACT):** Meaningfully better average job completion time and cluster utilization versus schedulers that only reallocate resources without also adapting training-time hyperparameters, because it closes the loop between "how much compute you give a job" and "how much that job can actually use well at that allocation."

**Limitations (FACT/OUR INTERPRETATION):** The efficiency-throughput tradeoff curve is specific to gradient-descent training dynamics (batch size vs. statistical efficiency); it doesn't generalize directly to arbitrary task types. Still requires online profiling infrastructure and job cooperation (jobs must accept dynamically changed batch sizes).

**GhostRange relevance (OUR INTERPRETATION, this is the most conceptually important paper here):** "Goodput" (useful progress per unit resource, not raw throughput) is the closest existing academic concept to GhostRange's *expected_evidence_gain / estimated_execution_cost* framing in the priority formula. Pollux's central lesson — don't just track whether a job is running fast, track whether it's producing *useful progress* per resource unit, and re-derive that estimate online as you observe the job rather than trusting only the upfront estimate — is exactly the argument for making GhostScheduler recompute `expected_evidence_gain` and `uncertainty_reduction` as tasks actually run, not just at task creation.

**What NOT to infer:** Don't infer that GhostRange should adopt gradient-descent-specific batch-size tuning — there's no analogous knob for most remediation-verification tasks. Don't infer Pollux's exact goodput formula transfers numerically; only the *shape* (throughput × value-density, re-estimated online) transfers.

**Implementation idea for GhostScheduler:** Treat `expected_evidence_gain` as a *live, re-estimated* quantity, not a static field set once at task creation — as a task/world executes and partial evidence streams in, recompute a running "evidence per elapsed cost" rate (a direct goodput analog) and feed it back into the `priority` recomputation loop on a fixed cadence, with the recompute event itself carrying a reason code (e.g., contributing to `MARGINAL_GAIN_LOW` when the running rate falls below a floor).

---

## 6. General patterns from serverless / autoscaling / deadline-aware scheduling (non-paper-specific, marked accordingly)

The following are broadly-known patterns in the serverless and autoscaling scheduling literature (e.g., work on cold-start-aware serverless scheduling, deadline-aware batch scheduling in systems like YARN/Borg-descended schedulers, and cluster fragmentation studies). I know these as general, well-established systems patterns rather than being able to cite a specific single paper with full confidence, so I present them as **[GENERAL KNOWLEDGE, not a specific citation]** rather than attributing them to a named paper I might misremember:

- **Cold-start amortization (serverless):** Serverless schedulers keep a pool of "warm" containers because cold-start latency dominates short-task overhead. **GhostRange relevance:** if world-fork setup (spinning a new disposable cyber world) has meaningful cold-start cost, GhostScheduler should track a `warm pool` of pre-provisioned world templates for the most common `task_type`s, and cost-model that against `estimated_execution_cost`.
- **Deadline-aware scheduling (EDF-style, Earliest-Deadline-First, and its cluster adaptations):** classic real-time scheduling theory (Liu & Layland-style, **[APPROXIMATE attribution]**) shows EDF is optimal for single-resource deadline feasibility but degrades under overload without admission control. **GhostRange relevance:** if an investigation has an operator-set time budget, a deadline term could modulate `priority`, but per Decisions.md's "not sacred" note, deadline urgency should be a distinct, explainable multiplicative or additive term, not silently folded into `expected_evidence_gain`.
- **Fragmentation in multi-resource bin packing:** heterogeneous GPU/CPU clusters suffer internal fragmentation when large-GPU-count jobs can't find contiguous/topologically-close capacity even though aggregate free capacity exists (a pattern documented across multiple cluster-scheduling papers, Tetris among them). **GhostRange relevance:** GPU-hungry adversarial-simulation tasks competing with many small CPU verification tasks risk exactly this fragmentation; the `PLACEMENT_SCORE` idea above should explicitly reserve/pack GPU-capable nodes rather than let small CPU tasks fragment them.

---

## Cross-cutting synthesis for GhostScheduler v0

1. **Separate concerns into three layers**, matching where each paper actually operates:
   - *Value layer* (is this worth running at all — `priority`, reason codes `DEPENDENCY_CRITICAL`, `HIGH_ASSET_RISK`, `HIGH_UNCERTAINTY`, `CHEAP_INFORMATION_GAIN`, `BRANCH_LOW_VALUE`, `BUDGET_EXHAUSTED`, `MARGINAL_GAIN_LOW`) — no surveyed paper solves this; it's GhostRange's genuine novel contribution and must stay simple/explainable/deterministic first.
   - *Placement layer* (given approved tasks, which node — Tetris-style alignment score, Sparrow-style bounded probing for the low-stakes dispatch path).
   - *Runtime-adaptation layer* (once running, is the resource allocation still justified — Gandiva-style GPU introspection → `GPU_ACCELERATION_EXPECTED`/`GPU_NOT_JUSTIFIED`; Pollux-style live re-estimate of value-per-cost → feeds back into value layer).
2. **Do not import fairness-across-tenants framing (Themis)** as a top-level goal; GhostRange's "unfairness by design" (starving low-value branches) is a feature, and reason code `BRANCH_LOW_VALUE` should be read as the intentional, explainable opposite of Themis's goal.
3. **Straggler detection** (reason code `STRAGGLER_DETECTED`) is covered in depth in `SPECULATION.md` (Agent 09's deliverable) rather than here, since it's a distinct research thread (MapReduce speculative execution / hedged requests), but note the overlap: Gandiva's introspection mechanism (sampling live task progress signals) is the same *kind* of instrumentation a straggler detector needs — GhostScheduler should build one shared "live task telemetry" subsystem that feeds both the GPU-justification check and straggler detection, not two separate polling systems.

## Explicit gaps / what I did not find high-confidence sources for

- I do not have confident, specific-paper-level knowledge of a scheduler purpose-built for adversarial/red-team cyber-range workloads specifically (as opposed to ML training or generic batch/serverless jobs) — I found none that I can cite honestly. This is consistent with GhostScheduler being genuinely novel territory, not a re-implementation of prior art.
- I do not have confident specific-paper knowledge of an "LLM-serving scheduler" system to cite by name for this document (the task prompt suggested this as a category); rather than invent a title/venue, I've omitted it. If one is needed for M2, this should be a targeted follow-up research task, not filled in from memory now.
