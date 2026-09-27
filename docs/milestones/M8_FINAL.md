# M8 Final — Adversarial Verification Engine (in progress)

**Status:** Core falsification loop + auth-lab benchmark scenario implemented; full §122 gate **not** met.

## What is a counterexample?

An **authorized**, **evidence-backed** execution sequence where a deterministic oracle shows the claim’s `FalsificationConditionV1` holds (e.g. unauthenticated privileged `/admin` access). LLM suspicion alone is not a counterexample.

## Claim → falsification condition

`FalsificationConditionV1` binds to `claim_id` with a machine-check id (`unauthenticated_admin_access`) and required observation fields.

## Search dimensions (v1)

HTTP request path/headers/identity for auth-lab; extensible via `SearchArmKind` and `MutationOperatorV1`.

## Safety

`assert_candidate_in_range` — asset allowlist, no public IPs, synthetic credentials only, bounded sequence length/payload.

## Oracle

`SecurityOracleV1` + `evaluate_oracle` — HTTP status/body + unauthenticated check.

## Differential testing

`interpret_differential` compares baseline vs remediated oracle satisfaction.

## GhostScheduler search allocation

`select_arm` implements `UNIFORM_RANDOM`, `ROUND_ROBIN`, `STATIC_PRIORITY`, `NOVELTY_GREEDY`, `GHOSTSCHEDULER_SEARCH` (novelty/counterexample-weighted).

## Benchmarks (initial)

Hidden ground truth: `benchmarks/m8/ground_truth/auth_admin_header_bypass.json` (evaluators only). In-process `AuthAdminLabScenario` discovers `X-Forwarded-User: admin` bypass against incomplete Fix B.

## Policies compared

Unit tests exercise discovery under `UNIFORM_RANDOM` and `GHOSTSCHEDULER_SEARCH`; full policy matrix + budget curves **not** run yet.

## Confirmation / minimization

Delta-style `minimize_sequence`; `confirm_counterexample` replays on fresh executor instance.

## GhostLedger

Hooks stubbed — search runs not yet sealed into bundles.

## Live Vultr

Not run — in-process scenario only.

## Remaining mocked / open

API endpoints, UI search worlds, Vultr disposable worlds, LLM hypothesis backend, full security test matrix, browser E2E, benchmark artifacts under `artifacts/benchmarks/m8/`.

## Ready for M9

Claim-bounded search primitives and honest reporting strings — foundation for **autonomous experiment design** (choose next experiment under budget).
