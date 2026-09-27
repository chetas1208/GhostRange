# M17 GhostShield — coordination (52 specialists)

Lead agent owns: formal semantics, trust boundary, contract arbitration, integration, benchmark integrity, live-cloud safety, release gating.

| agent_id | mission | owned_paths | status | live_enforcement_required |
|----------|---------|-------------|--------|---------------------------|
| 01 | M17 audit lead | `docs/milestones/M17_AUDIT.md` | DONE | no |
| 02 | Formal methods research | `docs/research/M17_RUNTIME_ASSURANCE_SYNTHESIS.md` | DONE | no |
| 03 | Trust model | `docs/security/GHOSTSHIELD_TRUST_MODEL.md` | DONE | no |
| 04 | TCB minimization | `docs/architecture/GHOSTSHIELD.md` | DONE | no |
| 05 | Canonical action architect | `packages/contracts/.../ghostshield_m17.py` | DONE | no |
| 06 | Canonicalization engineer | `CanonicalActionV1.canonical_digest` | DONE | no |
| 07 | Policy language | `docs/security/GHOSTSHIELD_POLICY_MODEL.md` | DONE | no |
| 08 | Policy evaluator | `policy_engine.py` | DONE | yes |
| 09 | Authorization verdict | `AuthorizationVerdictV1` | DONE | yes |
| 10 | Action permit | `ActionPermitV1` + `issue_permit` | DONE | yes |
| 11 | Execution gateway | `execution_gateway.py` | DONE | yes |
| 12 | State-bound auth / TOCTOU | gateway re-check + `STATE_STALE` | PARTIAL | yes |
| 13 | Budget authorization | policy `BUDGET_HARD_CAP` | PARTIAL | yes |
| 14 | Ownership authorization | P1 terminate | PARTIAL | yes |
| 15 | Human approval | P8 rollback | PARTIAL | yes |
| 16 | Break-glass | — | TODO | yes |
| 17 | TLA+ model architect | `formal/m17/WorkerFleet.tla` | PARTIAL | no |
| 18 | TLA+ worker/fleet | `WorkerFleet.tla` | PARTIAL | no |
| 19 | TLA+ lease | — | TODO | no |
| 20 | TLA+ recovery | — | TODO | no |
| 21 | TLA+ budget | — | TODO | no |
| 22 | TLA+ GhostWatch | — | TODO | no |
| 23 | Model-check automation | `artifacts/formal/m17/` | TODO | no |
| 24 | Counterexample translation | — | TODO | no |
| 25 | Refinement mapping | `docs/architecture/FORMAL_MODEL_MAPPING.md` | DONE | no |
| 26 | Runtime monitor architect | `runtime_monitor.py` | STUB | yes |
| 27 | Temporal properties | — | TODO | no |
| 28 | Obligation monitor | — | TODO | no |
| 29 | Director contract | `docs/architecture/RUNTIME_VERIFICATION.md` | PARTIAL | no |
| 30 | Scheduler contract | same | PARTIAL | no |
| 31 | Worker contract | same | PARTIAL | no |
| 32 | GhostWatch contract | same | TODO | yes |
| 33 | GhostMesh contract | same | TODO | no |
| 34 | Contract composition | — | TODO | no |
| 35 | Authorization evidence | `AuthorizationEvidenceV1` | CONTRACT_ONLY | yes |
| 36 | GhostLedger assurance | — | TODO | yes |
| 37 | Assurance case | `docs/research/M17_FORMAL_ASSURANCE_RESULTS.md` | PARTIAL | no |
| 38 | Assurance coverage matrix | M17_FINAL table | PARTIAL | no |
| 39 | Property-based tests | — | TODO | no |
| 40 | Adversarial traces | `artifacts/benchmarks/m17/` | TODO | no |
| 41 | Shadow mode | `GhostShieldMode.SHADOW` | DONE | yes |
| 42 | Performance | — | TODO | yes |
| 43 | Static bypass detection | `test_ghostshield_bypass_audit.py` | DONE | no |
| 44 | Prompt-injection red team | — | TODO | no |
| 45 | Compromised scheduler | unit via policy | PARTIAL | no |
| 46 | TOCTOU red team | `test_policy_p2.py` | PARTIAL | no |
| 47 | Permit replay/mutation | gateway tests | PARTIAL | yes |
| 48 | Live Vultr enforcement | — | BLOCKED | yes |
| 49 | Execution 3D UI | `packages/ui-3d/src/shield/*` | PARTIAL | no |
| 50 | Evidence assurance UI | Evidence inspector | TODO | no |
| 51 | Research integrity | synthesis doc | DONE | no |
| 52 | Independent final reviewer | `docs/milestones/M17_FINAL.md` | NO-GO | yes |

**Waves:** 0–1 executed; 2–10 open.

**Blockers:** M16 side-effect journal; Vultr API ACL; `orchestrator`/`vultr_adapter` gateway routing; TLC in local CI.
