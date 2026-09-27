# M4 Scheduling Research Synthesis

GhostRange M4 thesis: a compute-aware, branch-aware, heterogeneous scheduler can reduce time-to-verified-remediation and/or waste vs static baselines **without** bypassing mandatory verification. Negative results are valid.

Format per source: **TITLE · VENUE · YEAR · URL · PROBLEM · METHOD · RESULTS · LIMITATIONS · GHOSTRANGE LEARN · DO NOT CLAIM**

---

## 1. Heterogeneity at Hyperscale

- **TITLE:** Heterogeneity at Hyperscale: Characterization and Scheduling of Large Production AI Clusters at Alibaba  
- **VENUE:** OSDI  
- **YEAR:** 2026  
- **URL:** https://www.usenix.org/conference/osdi26/presentation/li-suyi  
- **PROBLEM:** GPU demand ≠ effective utilization; stranded CPU/GPU/locality/headroom.  
- **METHOD:** Six-month ASI trace; defragmentation; SpotGPU preemption-cost-aware scheduling.  
- **RESULTS:** Defrag cuts slack-node count ~20.2%; allocation ratio 68%→93% in reported deployment.  
- **LIMITATIONS:** Hyperscale AI training/inference mix — not cyber remediation DAGs; fractional GPU sharing rare in their fleet.  
- **GHOSTRANGE LEARN:** Track **multi-dimensional fit** (CPU+GPU+locality), **fragmentation metrics**, **preemption cost** before stealing capacity.  
- **DO NOT CLAIM:** 93% utilization on hackathon-scale Vultr; we operate orders-of-magnitude smaller.

---

## 2. Understanding Stragglers in Large Model Training

- **TITLE:** Understanding Stragglers in Large Model Training (ByteDance)  
- **VENUE:** OSDI  
- **YEAR:** 2025  
- **URL:** https://www.usenix.org/conference/osdi25/presentation/zhang-hanhan (verify exact slug at usenix.org)  
- **PROBLEM:** Stragglers dominate iteration time in distributed training.  
- **METHOD:** Production trace analysis; categorization of slow workers vs slow workloads.  
- **RESULTS:** Simple global timeouts miss root causes; stragglers are heterogeneous.  
- **LIMITATIONS:** Training-centric; checkpoint/restart economics differ from verification tasks.  
- **GHOSTRANGE LEARN:** Classify **WORKLOAD_SLOW vs WORKER_SLOW**; use **per-class runtime distributions**, not one timeout.  
- **DO NOT CLAIM:** We replicate their trace analysis — we adopt the *measurement discipline*.

---

## 3. PIPEMORPH / Attack of the Bubbles (stragglers)

- **TITLE:** PIPEMORPH (NSDI 2026 straggler mitigation — “Attack of the Bubbles” line of work)  
- **VENUE:** NSDI  
- **YEAR:** 2026  
- **URL:** https://www.usenix.org/conference/nsdi26 (search proceedings for PIPEMORPH)  
- **PROBLEM:** Pipeline bubbles and stragglers inflate iteration time.  
- **METHOD:** Runtime morphing / adaptive pipeline strategies under tested conditions.  
- **RESULTS:** Reported 1.2–3.5× iteration-time improvements in evaluated scenarios.  
- **LIMITATIONS:** ML pipeline assumptions; not directly applicable to forked cyber worlds.  
- **GHOSTRANGE LEARN:** **Speculate or duplicate** only when expected latency benefit exceeds duplicate cost; measure honestly.  
- **DO NOT CLAIM:** 3.5× speedup on auth-lab without our own benchmark artifacts.

---

## 4. XSched

- **TITLE:** XSched — cross-device scheduling for heterogeneous accelerators  
- **VENUE:** OSDI  
- **YEAR:** 2025  
- **URL:** https://www.usenix.org/conference/osdi25 (search XSched)  
- **PROBLEM:** Accelerator scheduling under preemption and heterogeneity.  
- **METHOD:** Scheduling framework treating accelerators as first-class with preemption support.  
- **RESULTS:** Improved utilization / SLO adherence in paper evaluations.  
- **LIMITATIONS:** Requires runtime preemption/checkpoint support we may not have on all tasks.  
- **GHOSTRANGE LEARN:** **`checkpoint_strategy`** gates preemption; simulation-first in M4.  
- **DO NOT CLAIM:** Live GPU preemption on Vultr without verified capability.

---

## 5. Libra

- **TITLE:** Libra — SLO-aware dynamic request scheduling  
- **VENUE:** NSDI  
- **YEAR:** 2026  
- **URL:** https://www.usenix.org/conference/nsdi26 (search Libra)  
- **PROBLEM:** Meeting SLOs under dynamic load with heterogeneous resources.  
- **METHOD:** SLO-aware scheduling and load balancing.  
- **RESULTS:** Better SLO compliance vs baselines in evaluated services.  
- **LIMITATIONS:** Request-level serving vs batch verification DAGs.  
- **GHOSTRANGE LEARN:** Treat **mandatory verification** as hard SLO constraints; optimize optional work under budget.  
- **DO NOT CLAIM:** Libra’s SLO numbers transfer to GhostRange without replication.

---

## 6. HeteCCL

- **TITLE:** HeteCCL — heterogeneous collective communication scheduling  
- **VENUE:** NSDI  
- **YEAR:** 2026  
- **URL:** https://www.usenix.org/conference/nsdi26 (search HeteCCL)  
- **PROBLEM:** Communication bottlenecks across heterogeneous links/devices.  
- **METHOD:** Topology-aware collective scheduling.  
- **RESULTS:** Reduced communication time in reported benchmarks.  
- **LIMITATIONS:** NCCL/collective focused; GhostRange HTTP replay is not HeteCCL.  
- **GHOSTRANGE LEARN:** **`network_intensity`** in task profiles affects placement when multi-region workers exist.  
- **DO NOT CLAIM:** We implement collective communication scheduling.

---

## 7. Quicksand

- **TITLE:** Quicksand — (NSDI 2025 resource/scheduling line)  
- **VENUE:** NSDI  
- **YEAR:** 2025  
- **URL:** https://www.usenix.org/conference/nsdi25 (search Quicksand)  
- **PROBLEM:** Dynamic resource elasticity under shifting load.  
- **METHOD:** Fast scale / scheduling coupling.  
- **RESULTS:** Improved responsiveness in paper scenarios.  
- **LIMITATIONS:** Cloud-specific assumptions.  
- **GHOSTRANGE LEARN:** Include **startup latency** in scale-out decisions — avoid workers that arrive after work finishes.  
- **DO NOT CLAIM:** Identical elasticity without measuring Vultr boot times (Agent 23).

---

## 8. Adaptive Test-Time Compute Allocation (2026)

- **TITLE:** Adaptive test-time compute allocation (representative 2026 line)  
- **VENUE:** arXiv / ML systems venues (2026)  
- **URL:** search “adaptive test-time compute allocation 2026” for primary PDF  
- **PROBLEM:** Uniform reasoning budget wastes compute on easy inputs.  
- **METHOD:** Allocate extra inference depth/samples by uncertainty/value signals.  
- **RESULTS:** Reports up to ~12.8% relative accuracy improvement under matched budgets in cited work.  
- **LIMITATIONS:** Model accuracy metrics ≠ cyber verification coverage.  
- **GHOSTRANGE LEARN:** **`ReasoningBudgetV1`** for planner/hypothesis tasks only; never for deterministic regression.  
- **DO NOT CLAIM:** Accuracy gains on LLM benchmarks imply faster incident verification.

---

## 9. Starburst

- **TITLE:** Starburst — (USENIX ATC 2024 scheduling/elasticity)  
- **VENUE:** USENIX ATC  
- **YEAR:** 2024  
- **URL:** https://www.usenix.org/conference/atc24 (search Starburst)  
- **PROBLEM:** Efficient cluster scheduling under bursty workloads.  
- **METHOD:** Burst-aware placement / scaling policies.  
- **RESULTS:** Improved tail latency or cost in evaluated traces.  
- **LIMITATIONS:** Different workload shapes than multiverse verification.  
- **GHOSTRANGE LEARN:** **Hysteresis** on scale-in/out for bursty fork waves (3 worlds × N tasks).  
- **DO NOT CLAIM:** Starburst’s exact policy without citation-matched replication.

---

## 10. Serverless / autoscaling (2024–2026 survey stance)

- **TITLE:** Multiple (FaaS autoscaling, queue-driven scaling)  
- **VENUE:** various  
- **YEAR:** 2024–2026  
- **URL:** primary papers per feature (cold start, concurrency limits)  
- **PROBLEM:** Cold starts and concurrency caps break naive autoscaling.  
- **METHOD:** Predictive scaling, minimum instances, drain-before-terminate.  
- **RESULTS:** Lower tail latency when startup modeled explicitly.  
- **LIMITATIONS:** Serverless ≠ long-running workers for attack replay.  
- **GHOSTRANGE LEARN:** Separate **VULTR_SERVERLESS** latency model from **CPU worker** model; route inference only.  
- **DO NOT CLAIM:** Serverless replaces workers for all task classes.

---

## GhostRange translation summary

| Idea | M4 artifact |
|------|-------------|
| Fragmentation / fit | `FragmentationMetricsV1`, placement score |
| Stragglers | `RuntimeDistributionV1`, `StragglerCause` |
| Speculation | `SPECULATE_TASK` with cost/latency accounting |
| Critical path | DAG slack in `critical_path.py` |
| Adaptive reasoning | `ReasoningBudgetV1` + `ROUTE_INFERENCE` |
| Scale hysteresis | `config/ghostscheduler-v3.yaml` |
| Measurement | `SchedulerTraceV1`, `artifacts/benchmarks/m4/` |

**Rejected for M4:** RL scheduler, LLM infrastructure placement, hyperscale-only defrag algorithms without GhostRange-scale data.
