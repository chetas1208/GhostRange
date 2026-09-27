# M15 adaptive scheduling — research synthesis

GhostRange M15 adopts **measured, workflow-aware, cost-aware** scheduling. LLMs may advise; **deterministic policy + budgets** provision compute.

---

## Cortex (workflow-aware agentic serving)

| Field | Content |
|-------|---------|
| **Title** | Cortex: Workflow-Aware Resource Pooling and Scheduling for Agentic Serving |
| **Authors** | Yeounoh Chung, Arvind Krishnamurthy, Kostis Kaffes, Nikos Pagonas |
| **Venue** | 1st Workshop on Systems for Agentic AI (SAA 2025) at SOSP |
| **Year** | 2025 |
| **URL** | https://arxiv.org/abs/2510.14126 |
| **Problem** | Shared pools couple heterogeneous agent stages → KV-cache bloat, tail latency, poor predictability |
| **Workload** | Multi-stage agentic graphs (e.g. NL2SQL: generate → execute → fix) |
| **Resource model** | Per-stage **engine pools** (homogeneous workers), stage-local queues/caches |
| **Objective** | Throughput, tail latency, SLO slack |
| **Algorithm** | Graph-aware orchestrator + SLO-slack priority + locality routing + per-stage scaling |
| **Results** | Better KV utilization vs shared engines; stage-local latency models |
| **Limitations** | Agentic **inference** serving, not cyber-range VM provisioning; prototype |
| **GhostRange translation** | **Stage isolation** as hypothesis for Director phases (design vs execute vs verify)—benchmark vs blind adopt |
| **Adopt** | Workflow position tracking; slack-aware priority; **speculation as future mechanism** (they propose branch speculation) |
| **Reject** | 1:1 GPU pool assumption for all GhostRange tasks; LLM-stage-only focus |
| **Must not claim** | “Cortex-validated GhostRange autoscaling” without our benchmarks |

---

## AgServe (session-aware cost/quality)

| Field | Content |
|-------|---------|
| **Title** | Transcending Cost-Quality Tradeoff in Agent Serving via Session-Awareness |
| **Authors** | Yanyu Ren, Li Chen, Dan Li, Xizheng Wang, Zhiyuan Wu, Yukai Miao, Yu Bai |
| **Venue** | NeurIPS 2025 |
| **Year** | 2025 |
| **URL** | https://proceedings.neurips.cc/paper_files/paper/2025/hash/04132e28265a355456f86a1c3fec3bcd-Abstract-Conference.html |
| **Problem** | Agent sessions need KV reuse + model cascade + dynamic GPU allocation |
| **Workload** | Multi-turn agent sessions |
| **Resource model** | GPUs across model tiers; dynamic scheduler by demand/supply |
| **Objective** | Cost vs quality Pareto |
| **Algorithm** | Session-aware cache (ETA eviction), Q/R judges for model cascade, resource scheduler |
| **Results** | ~GPT-4o quality at ~16.5% cost (their testbed) |
| **Limitations** | Inference serving stack; not DAG cyber workloads |
| **GhostRange translation** | **Session/campaign-aware** quality-vs-cost stopping; marginal value over rounds |
| **Adopt** | Separate **quality signal** from **compute economics** (Director vs Scheduler) |
| **Reject** | Direct AgServe stack for Vultr workers |
| **Must not claim** | GhostRange achieves AgServe numbers without replication |

---

## LarS (LLM scheduling — validate, don’t trust)

| Field | Content |
|-------|---------|
| **Title** | LLM-based cost-aware task scheduling for cloud computing systems (LarS) |
| **Authors** | Pei et al. |
| **Venue** | Journal of Cloud Computing, 2025 |
| **Year** | 2025 |
| **URL** | https://doi.org/10.1186/s13677-025-00822-0 |
| **Problem** | Heterogeneous cloud VMs; multi-objective scheduling |
| **Workload** | Cloud tasks on VMs |
| **Resource model** | VM pools |
| **Objective** | Response time, success rate, **rental cost** |
| **Algorithm** | DRL validates LLM trajectories → fine-tune LLM (LoRA) |
| **Results** | Beats baselines on cost/latency in paper environments |
| **Limitations** | LLM as decision agent risks unsafe actions |
| **GhostRange translation** | Inference may **suggest** placement features; **DRL/validator not required** for M15 v1 |
| **Adopt** | **Validate** any model advice against budget/allowlist (LarS lesson) |
| **Reject** | LLM directly calling Vultr API |
| **Must not claim** | “LLM schedules GhostRange” — policy decides |

---

## Classical anchors (implementation baselines)

| Family | GhostRange use |
|--------|----------------|
| **HEFT / CPOP / list scheduling** | Heterogeneous DAG baseline (Wave 6 agent 37) |
| **Critical path method (CPM)** | `CriticalPathReportV1` — implemented for `ExecutionDAGV2` |
| **Bin packing / gang scheduling** | Warm worker + multi-task packing evaluation |
| **Speculative / hedged execution** | Straggler mitigation with **waste metrics** |
| **Multi-objective / Pareto** | Primary reporting: cost vs makespan vs evidence yield |

---

## GhostRange M15 design commitments (from synthesis)

1. **Workflow-aware** — DAG dependencies, dynamic critical path, not queue-length autoscaling alone.  
2. **End-to-end CPU vs GPU** — include **startup + queue + transfer** (`ComputeCrossoverModelV1`).  
3. **Director ≠ Scheduler** — information value vs dollars.  
4. **Simulator-first** — `GhostSchedulerSimulatorV2` (discrete-event) before elastic live fleet.  
5. **Live gates** — real-worker GO; `ALLOW_M15_TWO_WORKER_TEST`; `ALLOW_LIVE_GPU_TEST`; `MAX_ACTIVE_WORKERS` caps.  
6. **Report negative results** — FIFO / one-worker / HEFT may win on some DAGs.

---

## References (short)

- Chung et al., Cortex, arXiv:2510.14126, 2025.  
- Ren et al., AgServe, NeurIPS 2025.  
- Pei et al., LarS, J. Cloud Computing 2025, doi:10.1186/s13677-025-00822-0.  
- Standard texts: HEFT (Topcuoglu et al.); CPM; OR scheduling surveys.
