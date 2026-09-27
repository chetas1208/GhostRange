# GhostEvolve

Verified operational experience → versioned **candidates** → offline evaluation → regression → shadow → human approval → GhostShield `PROMOTE_EVOLUTION_CANDIDATE` → canary → champion.

**Central rule:** experience may **propose** change; it may **not** directly change production behavior.

Package: `packages/ghostevolve/`.

First learning surface: `SCHEDULER_RUNTIME_ESTIMATOR` (`runtime-estimator:v4-m15` champion vs EWMA candidate).

Forbidden: GhostShield hard invariants, secrets, hard budgets, arbitrary code patch.
