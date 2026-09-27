# M16 reliability synthesis

GhostRuntime applies **workflow-engine and SRE principles** without replacing GhostRange with Temporal/K8s. Canonical state lives in **PostgreSQL**; large blobs in **Object Storage**.

---

## Long-horizon agent reliability (2026)

### HORIZON — horizon-dependent degradation

| Field | Content |
|-------|---------|
| **Title** | The Long-Horizon Task Mirage? Diagnosing Where and Why Agentic Systems Break |
| **Venue** | arXiv / HORIZON leaderboard |
| **Year** | 2026 |
| **URL** | https://arxiv.org/html/2604.11978 |
| **Failure model** | Nonlinear success collapse as intrinsic horizon grows; domain-specific |
| **Method** | Controlled task families + trajectory failure taxonomy |
| **Recovery model** | Diagnostic (not a runtime) |
| **GhostRange** | **ReliabilityBudgetV1** tracks `dependent_step_count` vs success — not pass@1 alone |
| **Adopt** | Horizon sweeps (5→160 steps) in `artifacts/benchmarks/m16/horizon/` |
| **Reject** | LLM-as-judge for production recovery decisions |
| **Must not claim** | “Agents reliable” without horizon curve |

### Beyond pass@1 — reliability science framework

| Field | Content |
|-------|---------|
| **Title** | Beyond pass@1: A Reliability Science Framework for Long-Horizon LLM Agents |
| **Year** | 2026 |
| **URL** | https://arxiv.org/pdf/2603.29231 |
| **Failure model** | RDC, VAF, GDS, MOP (meltdown) |
| **GhostRange** | Report **graceful degradation** (`CapabilityDegradationV1`) and partial campaign completion |
| **Adopt** | Repeated trials (k>1), duration buckets |
| **Reject** | Naive memory scaffold as reliability fix |

### Horizon residual (trajectory-induced degradation)

| Field | Content |
|-------|---------|
| **Title** | Benchmarking the Residual: What Long-Horizon Evaluations Add Beyond Matched Short-Task Performance |
| **Year** | 2026 |
| **URL** | https://arxiv.org/html/2607.27283v1 |
| **GhostRange** | Compare full campaign vs sum of short-stage predictions — detect history/state effects |

---

## Durable execution systems (principles extracted)

| System | Failure model | Recovery | GhostRange adoption |
|--------|---------------|----------|---------------------|
| **Temporal / Cadence** | Event history + deterministic replay | Replay from history | **DeterministicRuntimeReplayV1**; freeze model outputs |
| **Step Functions** | State machine + at-least-once tasks | Retry + catch | **SideEffectRecordV1** + idempotency |
| **Sagas** | Partial multi-step failure | Compensating transactions | **CompensationActionV1** — cloud is not 2PC |
| **Event sourcing** | Append-only log | Rebuild projections | `runtime_events` + existing `event_log` |
| **Borg/K8s reconcile** | Desired vs actual | Control loop | **GlobalResourceReconciler** (Vultr vs PG) |

**Reject:** Replacing GhostScheduler/Director with external orchestrator.  
**Reject:** Claiming exactly-once without proof.

---

## GhostRuntime guarantee (explicit)

**At-least-once** delivery and execution attempts, with:

- **Idempotent side-effect journal** (`campaign_id` + `idempotency_key` unique)
- **Canonical task result** single-row commit (compare-and-swap / PK on `task_id`)
- **Fencing** via `CampaignRuntimeLeaseV1` + monotonic `fencing_token`
- **UNKNOWN** provider states reconciled before retry create
- **Safe mode** blocks new billable effects when ownership/state uncertain

Target safety metrics (benchmark corpus): **duplicate consequential effect rate = 0**, **orphan rate after finalization = 0**.

---

## M16 killer demo (acceptance narrative)

Persist `CreateWorker` intent → Vultr succeeds → crash before DB commit → restart → reconcile → **adopt VM** → resume → evidence → teardown → `owned_workers == []`.

---

## References

- Chung et al., Cortex (workflow-aware serving), arXiv:2510.14126 — stage isolation lesson for bulkheads (M15/M16 boundary).  
- Temporal documentation — event history replay pattern.  
- HORIZON + reliability framework papers above.
