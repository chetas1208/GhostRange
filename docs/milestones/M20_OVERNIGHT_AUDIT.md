# M20 Overnight Audit

**Superseded in part (2026-09-27, later same day):** the P0 "No verified live Vultr Compute lifecycle" row and the "Vultr Compute worker lifecycle: NOT_RUN" classification below predate a real end-to-end single-worker lifecycle proven later the same day — see `docs/milestones/M2_CHECKPOINT_2026-09-27.md` and the current `docs/milestones/M20_FINAL.md`. The golden-campaign-triggered live worker (as one integrated run) still has not completed; that gap is real and current.

**Date:** 2026-09-27  
**Verdict:** `NO-SHIP` — local integration is testable; live deployment and several M20 release gates remain incomplete.

## Top remaining gaps

| Priority | Gap | Evidence / safe next step |
| --- | --- | --- |
| P0 | Current checkout is not deployed to the public control VM | Public `/health/ready` is healthy, but current campaign/scheduler/Director/Causal/GhostWatch/GhostMesh routes are absent. Deploy through the approved control-VM path. |
| P0 | No verified live Vultr Compute lifecycle for this checkout | Current runner is rejected by the Vultr token IP ACL before any create call. Run from the allowed control VM only with explicit authorization. |
| P0 | Public repository publication review | `chetas1208/GhostRange` exists on `main`; review the published commit and keep future pushes non-destructive. |
| P0 | Release maturity remains research prototype | M20 final review records `NO-SHIP`; do not relabel until gates are actually closed. |
| P1 | NetBird is not consumed by `RealWorkerOrchestrator` | Either complete enrollment/revocation wiring and tests or keep the integration explicitly optional. |
| P1 | Cost persistence needs a real Postgres restart acceptance | Code is wired conditionally through `CostLedgerPersistence`; add/run a database-backed restart test when local Postgres is available. |
| P1 | Timing persistence needs a real Postgres restart/percentile acceptance | `OperationTimingStore` supports samples and P50/P90/P95, but no full restart acceptance was run in this environment. |
| P1 | Provider invoice reconciliation is unavailable through the current API | Preserve `PROVIDER_UNAVAILABLE` / `NOT_SUPPORTED`; do not fabricate invoice totals. |
| P1 | Live campaign is not a successful 200 round trip | The previous live attempt reached real durable services and failed at live worker listing due to ACL. Re-run only after deployment/ACL correction. |
| P1 | Runtime restart/recovery is not part of one canonical M20 HTTP call | Keep the limitation visible; add a controlled recovery campaign before calling it integrated. |
| P1 | GhostCausal/GhostWatch/GhostMesh/GhostArena/GhostEvolve are not production-certified | Simulator/harness and API paths exist; keep their mode labels and NO-GO status. |
| P2 | Screenshot acceptance remains incomplete | Existing capture scripts and 24-frame specification exist; browser dependency prevented capture. |
| P2 | Interactive tour is TOUR-NO-GO pending human review | Use controlled replay; do not create billable resources for the tour. |
| P2 | No production telemetry claim | UI shows unavailable/derived data where backend does not expose real CPU/RAM/GPU metrics. |
| P2 | Baseline publication | Reviewed baseline and follow-up validation commits exist on public `main`. |
| P2 | Some older architecture docs still describe persistence as planned | Update stale wording where it conflicts with current wiring; preserve remaining limitations. |
| P3 | Minor visual polish and animation improvements | Defer until evidence, deployment, and acceptance gates close. |
| P3 | Broader benchmark corpus and multi-seed live Arena | Optional research work, not a reason to overstate M20 maturity. |

## Reality classification

| Area | Classification |
| --- | --- |
| Local mock golden campaign | `IMPLEMENTED_AND_TESTED` |
| Public HTTPS control VM | `CONTROLLED_LIVE` / `STALE_DEPLOYMENT` |
| Current-code live M20 campaign | `IMPLEMENTED_UNVERIFIED` / failed at worker-list step |
| Vultr Compute worker lifecycle | `NOT_RUN` from the allowed origin; ACL blocked from this runner |
| Serverless Inference worker pool | `REAL_LIVE` evidence recorded in M20 matrix when credentials are available |
| GhostDirector | `SIMULATED` campaign implementation |
| GhostScheduler | `IMPLEMENTED_AND_TESTED`; live placement gated |
| GhostCausal | `SIMULATED` / API transport |
| GhostWatch | `SIMULATED` rollout/conformance |
| GhostMesh | `CONTROLLED_REPLAY` / five-node harness |
| GhostLedger | `IMPLEMENTED_AND_TESTED` seal/verify path |
| GhostShield | `IMPLEMENTED_AND_TESTED` policy/bypass tests; live worker E2E unverified |
| GhostArena | `SIMULATED` independent evaluation |
| GhostEvolve | `IMPLEMENTED_UNVERIFIED` promotion gate; production NO-GO |
| Tactical UI | `IMPLEMENTED_AND_TESTED`; fixture/replay and live paths, visual sign-off pending |
| Cost ledger | `IMPLEMENTED_AND_TESTED`; durable hooks conditional on Postgres |
| Historical timing | `IMPLEMENTED_UNVERIFIED` for database-backed acceptance |

## Negative results preserved

- Public deployment route audit found the deployed build is stale; it is not safe to call the public URL a current-code demo.
- Live Vultr Compute validation failed with provider ACL `401 Unauthorized IP address` on a read-only list call; no instance was created and no spend occurred.
- Screenshot capture was not completed because the local browser environment lacked `libasound.so.2`.
- The release script initially failed six async tests because the root pytest configuration omitted `asyncio_mode = auto`; this was corrected and the full test matrix passed.
- No provider invoice-level campaign total was available through the current API; reconciliation remains explicit rather than invented.
