# Adversarial Verification Engine (M8)

GhostRange distinguishes **verification** (known tests) from **falsification search** (find a counterexample to a specific claim).

## Flow

```
ClaimV1 + FalsificationConditionV1
        → AdversarialSearchPlanV1
        → bounded SearchCandidateV1 stream
        → safety gate (asset allowlist)
        → world execute → SecurityOracleV1
        → minimize → confirm on fresh world
        → CounterexampleV1 | SURVIVED_BUDGET report
```

## Package

`packages/adversarial-verifier` — `run_adversarial_search(plan, executor)`.

Reference scenario: `AuthAdminLabScenario` (incomplete Fix B + hidden `X-Forwarded-User` bypass).

## GhostScheduler role

Search policies in `policies.py` allocate attempts across `SearchArmV1` families. This is separate from execution-task scheduling in M4 but uses the same “allocate compute where value is highest” principle.

## Safety

No arbitrary URLs; targets must be `authorized_asset_ids`. External IPs and metadata hosts rejected in `safety.py`.

## Honest outcomes

Reports use `AdversarialClaimPhase` and explicit strings — never “secure.”

## Not in v1 slice

Live Vultr worlds, UI probes, LLM hypothesis generation, GhostLedger sealing of search runs, full benchmark matrix.
