# M9 Experiment Design — Research Synthesis

GhostDirector selects **which experiment** to run under budget—not how to provision CPUs (GhostScheduler).

---

## Bayesian / optimal experimental design (BOED)

| Field | Detail |
|-------|--------|
| **Problem** | Choose experiments maximizing expected reduction in parameter/decision uncertainty |
| **Method** | Expected information gain (EIG) over posterior |
| **Limitation** | Requires explicit likelihood model; misspecified models yield pathological acquisitions |
| **GhostRange** | EIG as **one** strategy in `ExperimentUtilityV1`; not sole objective |
| **Must not claim** | "Optimal" without stated generative model |

---

## Robust Bayesian active learning (misspecification)

| Field | Detail |
|-------|--------|
| **Venue** | Recent AISTATS-line work on robust acquisition under model misspecification |
| **Problem** | Pure informativeness pursues artifacts of wrong model |
| **GhostRange** | `AcquisitionScoreV1` adds **representativeness**, **robustness_bonus**, **decision_value** |
| **Must not claim** | Robustness equals correctness under all adversarial worlds |

---

## Value of information (VoI)

| Field | Detail |
|-------|--------|
| **Problem** | Will this evidence change the remediation/claim decision? |
| **GhostRange** | `decision_relevance` on `UncertaintyItemV1`; low VoI after mandatory replay fails |
| **Must not claim** | Dollar-denominated VoI without calibrated decision model |

---

## Multi-armed bandits / best-arm identification

| Field | Detail |
|-------|--------|
| **GhostRange** | Experiment **policies** compared in simulator (`FIXED_SCRIPT`, `RANDOM_SAFE`, `GHOSTDIRECTOR_V1`) |
| **Rejected for M9** | RL-trained director (prompt §98) |

---

## Active testing / sequential hypothesis testing

| Field | Detail |
|-------|--------|
| **GhostRange** | Hypothesis graph + discriminating experiments with **expected outcomes** per hypothesis |
| **Stopping** | `DirectorStopReason` — guard **incorrect early stop** metric |

---

## AgentCyberRange / cyber ranges

| Field | Detail |
|-------|--------|
| **Relevance** | Experiments must **execute** in isolated multi-host worlds, not model text alone |
| **GhostRange** | Typed `ExperimentOperatorV1`; in-process simulator first, Vultr later |

---

## Adopted

1. Explicit `InvestigationKnowledgeStateV1` + qualitative uncertainty (no fake %)
2. Competing `InvestigationHypothesisV1` + graph edges
3. `ExperimentProposalV1` with pre-registered utility estimates
4. Portfolio selection + dominance pruning
5. Surprise → new hypothesis pathway
6. Director → `ExperimentExecutionDAGV1` → GhostScheduler (separate)

## Rejected

- LLM execution authority
- Single-number "AI confidence"
- Merging Director into Scheduler
