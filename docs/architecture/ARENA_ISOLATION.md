# Arena isolation

## Storage

- Hidden bundles: `evaluation/private/*.json` (gitignored).
- Public scenario descriptors: code + `artifacts/benchmarks/m19/` (no ground truth).

## Import boundary

- Production API (`apps/api`) must not import `ArenaHiddenStore` or paths under `evaluation/private`.
- Enforced by `packages/ghostarena/tests/test_isolation.py`.

## Network (target)

- Evaluator loads hidden verifiers from private storage inside evaluator process.
- Evaluated agent sandbox must not reach a network endpoint that returns hidden ground truth.

## Static leakage (target)

- Production container image scan must not contain `evaluation/private` content — **manual/CI scan TBD**.

## Learner holdout

- Active hidden trajectories are not written into `GhostExperienceStore`.
- Retired scenarios may be disclosed under rotation policy (not implemented).
