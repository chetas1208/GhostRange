# Arena verification

## Layers

| Verifier | Question |
|----------|----------|
| OutcomeVerifierV1 | Did external/hidden state match claimed success? |
| ProcessVerifierV1 | Forbidden intermediate action, skipped branch, budget misuse? |
| SafetyVerifierV1 | GhostShield-aligned caps and unsafe attempts? |
| TrajectoryVerifierV1 | Whole-trace consistency (step count, qualification class) |

## Run qualification

`SUCCESS_CLEAN`, `SUCCESS_WITH_RECOVERED_ERRORS`, `SUCCESS_WITH_POLICY_VIOLATION` (counts as safety failure), `FAILURE`, `INVALID_EVALUATION`.

## First failure

`FailureLocalizationV1` records earliest material error — e.g. premature stop before counterexample search completes.

Implementation: `packages/ghostarena/ghostrange_ghostarena/verifiers.py` (deterministic sim policies today).
