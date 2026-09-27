# M11 Coordination — GhostGate (32 specialists)

**Hard rule:** no production mutation. Approval ≠ deployed.

| Wave | agents | focus |
|------|--------|--------|
| 0 | 01–02 | Audit + research |
| 1 | 03–08 | Contracts + gates |
| 2 | 09–14 | Patches + risk |
| 3 | 15–21 | Rollout + rollback + post-change |
| 4 | 22–24 | Simulation + Director/Scheduler bridges |
| 5 | 25–27 | Approval + Ledger + bundle |
| 6 | 28–30 | UI (3 tabs only) |
| 7 | 31 | Security |
| 8 | 32 | GO/NO-GO |

| ID | mission | owned_paths | status |
|----|---------|-------------|--------|
| 01 | Audit | `M11_AUDIT.md` | done |
| 02 | Research | `M11_SAFE_PROMOTION_SYNTHESIS.md` | done |
| 03 | Contracts | `ghostgate_m11.py` | done |
| 04 | Equivalence | `equivalence.py` | done |
| 05 | Source drift gate | `gates.py` | done |
| 06 | Claim/fidelity gate | `gates.py` | done |
| 07 | Adversarial gate | `gates.py` | done |
| 08 | Change actions | `ghostgate_m11.py` | done |
| 09–11 | Patch gens | `patches.py` | partial |
| 12 | Minimization | deferred | open |
| 13 | Blast radius | `impact.py` | done |
| 14 | Risk profile | `risk.py` | done |
| 15–17 | Strategy | `strategy.py` | done |
| 18 | Rollback | `rollback.py` | done |
| 19 | DB semantics | `rollback.py` notes | partial |
| 20–21 | Post-change + obs | `verification.py` | done |
| 22 | Simulator | `simulator.py` | partial |
| 23–24 | Bridges | stubs | partial |
| 25 | Approval | `approval.py` | done |
| 26–27 | Ledger bundle | `bundle.py` | done |
| 28–30 | UI | `ProductionShadow.tsx` | started |
| 31 | Security tests | `test_security.py` | done |
| 32 | Review | `M11_FINAL.md` | NO-GO |
