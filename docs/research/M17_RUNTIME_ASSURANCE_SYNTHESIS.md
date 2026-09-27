# M17 — Runtime assurance synthesis

## NIST IR 8356 (Digital Twin Cybersecurity)

| Field | Content |
|-------|---------|
| TITLE | NIST IR 8356 — Considerations for Digital Twin Cybersecurity |
| AUTHORS | NIST |
| VENUE | NIST |
| YEAR | 2023 |
| URL | https://csrc.nist.gov/pubs/ir/8356/final |
| PROBLEM | DT integrity, trust, and security as first-class |
| FORMALISM | Guidance / controls taxonomy |
| GHOSTRANGE TRANSLATION | GhostShield = reference monitor on effectful twin actions |
| WHAT WE ADOPT | Trust boundaries, fail-closed on critical effects |
| WHAT WE REJECT | Claiming full DT certification |
| WHAT WE MUST NOT CLAIM | “NIST-compliant digital twin” |

## Formal Verification of Digital Twins with TLA (Huang et al., 2026)

| Field | Content |
|-------|---------|
| TITLE | Formal Verification of Digital Twins with the Temporal Logic of Actions |
| AUTHORS | Huang, Topcu, Varshney, Willcox (representative) |
| VENUE | Journal of Computational Physics |
| YEAR | 2026 |
| PROBLEM | Concurrency, async evolution, comm uncertainty in DT |
| FORMALISM | TLA+ / temporal logic of actions |
| PROPERTIES VERIFIED | Synchronization-style system properties (paper-specific) |
| GHOSTRANGE TRANSLATION | `WorkerFleet.tla` abstracts fleet cap; future lease/recovery modules |
| WHAT WE ADOPT | Small finite models + explicit assumptions |
| WHAT WE REJECT | Line-for-line production verification |
| LIMITATIONS | Abstraction gap; TLC state explosion |

## Execution-time authorization (agent governance literature)

| Field | Content |
|-------|---------|
| PROBLEM | LLM proposals must not be the security boundary |
| ENFORCEMENT MODEL | Canonicalize → policy → permit → gateway |
| GHOSTRANGE TRANSLATION | `CanonicalActionV1` → `GhostShieldPolicyEngine` → `GhostExecutionGateway` |
| WHAT WE MUST NOT CLAIM | “Prompt injection solved” — only protected paths are gated |

## Behavioral contracts

| Field | Content |
|-------|---------|
| PROBLEM | Component preconditions/forbidden actions at runtime |
| GHOSTRANGE TRANSLATION | `AgentBehaviorContractV1`; Director/Scheduler may propose, not authorize |
| WHAT WE ADOPT | Typed allowed/forbidden action lists |

## Property coverage split (honest)

| Kind | Share (M17 target set) |
|------|-------------------------|
| MODEL_CHECKED | P2 fleet cap (abstract) |
| RUNTIME_ENFORCED | P2, P1, P3, P11 on worker gateway path |
| RUNTIME_MONITORED | Trace obligations (L1–L3) — **TODO** |
| TESTED_ONLY | Bypass audit, ENFORCE mock races |
| NOT_COVERED | Full range provisioning, GhostWatch production control |
