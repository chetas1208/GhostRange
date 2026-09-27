# Rollback validation (M11)

GhostGate does **not** assume rollback works because a plan exists.

## In-range drill (M11)

1. Apply remediation in disposable twin  
2. Verify hardened behavior  
3. Execute rollback steps from `RollbackPlanV1` (simulated)  
4. Verify baseline restored  

Status recorded on the candidate: `UNTESTED` | `TESTED_PASS` | `TESTED_FAIL` | `PARTIAL` | `IRREVERSIBLE`.

## Language

> ROLLBACK PASSED IN THE RECORDED GHOSTRANGE TWIN.

Not guaranteed production rollback.

## Irreversible changes

Schema/data migrations may set `IRREVERSIBLE` or `MANUAL_RECOVERY_REQUIRED` — no fabricated rollback.
