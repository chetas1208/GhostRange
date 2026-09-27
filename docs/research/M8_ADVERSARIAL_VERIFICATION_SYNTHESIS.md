# M8 Adversarial Verification — Research Synthesis

GhostRange M8 translates **counterexample-guided** and **search-based testing** ideas into **claim-bounded falsification** inside authorized cyber ranges—not unrestricted offensive automation.

---

## Counterexample-guided repair / CEGIS

| Field | Detail |
|-------|--------|
| **Source** | Counterexample-guided inductive synthesis (CEGIS); recent LLM repair loops (e.g. AAAI 2025 counterexample-guided repair reports) |
| **Problem** | One-shot fixes pass tests but fail on unseen inputs |
| **Method** | Candidate → verify → counterexample → refine candidate |
| **Result** | Smaller, more test-aligned repairs when counterexamples feed back |
| **Limitation** | No proof of correctness; counterexamples only within verifier/search model |
| **GhostRange translation** | `AdversarialSearchPlanV1` + `CounterexampleV1` → `RemediationRevisionV1` |
| **Safety** | Search only on GhostRange-owned assets |
| **Must not claim** | "No counterexample" = secure |

---

## Property-based testing (Hypothesis, etc.)

| Field | Detail |
|-------|--------|
| **Source** | Hypothesis, QuickCheck family |
| **Problem** | Manual tests miss input combinations |
| **Method** | Generate structured inputs; shrink failures |
| **GhostRange translation** | Typed `MutationOperatorV1` + optional Hypothesis for HTTP fields |
| **Safety** | Generators bound to OpenAPI/world asset IDs |
| **Must not claim** | Full fuzzer replacement |

---

## Differential testing

| Field | Detail |
|-------|--------|
| **Source** | Differential testing (vulnerable vs patched builds) |
| **Method** | Same action sequence on two worlds; compare oracle outcomes |
| **GhostRange translation** | `DifferentialObservationV1` |
| **Must not claim** | Both failing implies security issue (may be broken test) |

---

## Metamorphic testing

| Field | Detail |
|-------|--------|
| **Source** | Metamorphic relations literature |
| **Example** | Irrelevant header reorder should not change authz |
| **GhostRange translation** | `metamorphic.py` relations on HTTP requests |
| **Must not claim** | All claims have metamorphic oracles |

---

## Greybox / coverage-guided fuzzing (AFL++, libFuzzer)

| Field | Detail |
|-------|--------|
| **Source** | AFL++, libFuzzer concepts |
| **GhostRange translation** | `ObservationNoveltyV1` (status/path/error novelty—not full edge coverage) |
| **Must not claim** | M8 builds a general-purpose fuzzer |

---

## Multi-armed bandits (UCB, Thompson)

| Field | Detail |
|-------|--------|
| **Source** | Bandit allocation literature |
| **GhostRange translation** | Baselines first (`UNIFORM_RANDOM`, `NOVELTY_GREEDY`, `GHOSTSCHEDULER_SEARCH`); UCB optional after benchmarks |
| **Must not claim** | Optimal search without measurement |

---

## Cyber-range evaluation (AgentCyberRange, CAIBench, CVE-Bench, CyberGym)

| Field | Detail |
|-------|--------|
| **AgentCyberRange** | Multi-host realistic ranges for adaptive agent evaluation |
| **CAIBench** | Knowledge ≠ adaptive attack/defense performance |
| **GhostRange translation** | Isolated worlds + reproducible oracles + benchmark ground truth held out |
| **Must not claim** | GhostRange scores equal benchmark leaderboard numbers |

---

## Active testing / experiment design (preview M9)

Inspect evidence gaps and choose the next experiment under budget—M8 provides falsification; M9 would prioritize **which** experiment reduces uncertainty.

---

## Adopted for M8 v1

1. Claim → `FalsificationConditionV1`  
2. Bounded mutations + search memory  
3. Deterministic `SecurityOracleV1` where possible  
4. Delta-style minimization (`LOCALLY_MINIMIZED`)  
5. Fresh-world confirmation count  
6. Scheduler-style arm allocation (`SearchArmV1`)  
7. Honest stop text: survived **budget**, not secure  

## Rejected for M8 v1

- Custom fuzzer from scratch  
- LLM as sole oracle  
- External IP / production targeting  
- Percent "security scores"
