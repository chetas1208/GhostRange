# M13 Final — GhostMesh

**Agent 40 verdict: NO-GO** — see `docs/milestones/AGENT_40_REVIEW.md` (40-agent campaign executed; live fleet + screenshots + durable ledger remain open)

## What is GhostMesh?

Privacy-preserving **defensive knowledge federation**. Structured, transformed artifacts cross a Mesh protocol; **raw local evidence stays local**.

## What is shared?

Abstract patterns (tags/relations), applicability profiles, provenance digests, privacy profiles, aggregated statistics (when cohort policy met).

## What never leaves a node (default)?

Hostnames, IPs, raw URLs, source code, raw logs, credentials, customer data, exact topology, raw counterexamples, production telemetry.

## M12 dependencies

M12 remains **NO-GO** for live adapters and full GhostLedger rollout stream. M13 demo uses **SIMULATED_MESH_HARNESS** only.

## Authority

Mesh has **no production authority**. No `RUN_COMMAND`, deploy, rollback, or remote Director control messages.

## Local validation rule

Remote knowledge → **prior/hypothesis** → GhostDirector ordering → local disposable experiment → **local claim**.

## Benchmark (simulated)

See `artifacts/benchmarks/m13/summary.json` after `python scripts/benchmark_m13.py`.

- Poison node E: quarantine path exercised
- Node B: mesh prior moves session-refresh probe first
- Node C: negative transfer / local reject
- Node D: NOT_APPLICABLE without experiment

## What remains mocked

Secure aggregation, DP aggregates in production path, FederatedPriorModel training, live Vultr VPC federation, full semantic privacy red team, 12 screenshots.

## Integrity language

- Say: *raw local evidence remains local; policy-approved transformed knowledge may be federated.*
- Do not say: *federated learning is inherently private.*
- Do not say: *remote knowledge is verified* — say *provenance-checked; locally validated.*

## M14 direction (suggested)

Operational federation governance at scale, optional TEE-backed aggregation research, stronger GhostLedger mesh attestations, live consortium pilot with explicit threat model sign-off.
