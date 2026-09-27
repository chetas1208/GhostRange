# M20 Final — GhostRange One

## Update (2026-09-27, later same day) — read this section first

This is the single top-level status document. Everything below the original Agent 59/60 review (kept
for the record) has been corrected against artifacts and code read directly in this pass, not against
other docs' prose. Taxonomy: `REAL_LIVE` (real external effect, no shortcuts) / `CONTROLLED_LIVE` (real
external service, gated or small-scale) / `SIMULATED` (in-process, no external effect) / `NOT_RUN`.

### Proven REAL_LIVE — genuinely happened, don't undersell these

| What | Evidence |
|------|----------|
| Public deployment reachable, HTTPS trusted | `http://45.76.248.45/`, `https://45.76.248.45.sslip.io/`, `https://45-76-248-45.nip.io/` all answer; the two domain forms carry trusted Let's Encrypt certs (no browser warning), the IP form is a plain-HTTP fallback. |
| One full real Vultr Compute worker lifecycle | Real VM created (`vc2-1c-1gb`, region `ewr`) → worker agent bootstrapped and registered with the control plane → real CPU benchmark ran on it (2,000,000 iterations, 436ms), result stored as a real Postgres artifact row → worker torn down → deletion confirmed via a **direct per-resource Vultr GET returning 404** (not an eventually-consistent list call). A teardown-race bug (false-negative 500 on a genuinely successful teardown) was found and fixed along the way. Full detail: `docs/milestones/M2_CHECKPOINT_2026-09-27.md`. This is a real, narrow, single-worker proof — it is **not** the same thing as the golden campaign creating a worker as part of one integrated run (see gap below). |
| 10 real concurrent Vultr Serverless Inference calls | `inference_worker_pool.py` + `/v1/scheduler/inference-workers/dispatch`: 10 concurrent real HTTP calls to `https://api.vultrinference.com/v1/chat/completions`, distinct request IDs, `max_observed_concurrency=10`, GhostShield-mediated, hard-capped at `MAX_ACTIVE_INFERENCE_WORKERS<=10` / `INFERENCE_WORKER_MAX_USD<=$25` per session, `spent_usd≈$0.50` observed. Budget-cap-of-$0.03 test hard-refused all 3 tasks with `$0.00` spent (fails closed). See `docs/release/M20_REALITY_MATRIX.md` and `apps/api/tests/test_inference_worker_pool.py`. |
| GhostShield policy-bypass found and closed — two separate gaps | (1) `M2OneWorldOrchestrator` built a raw, unmediated Vultr provider with zero gateway mediation, reachable via the live campaign route — closed via `ShieldedVultrAdapter`. (2) `list_computes(range_id=None)` returned every Vultr instance in the account regardless of GhostRange's ownership tag, making the ownership check a no-op during teardown (exactly how `terminate_worker()` calls it) — closed by filtering on the ownership tag in both real and mock providers. Both fixed and tested 2026-09-27; see `docs/security/GHOSTSHIELD_BYPASS_ANALYSIS.md`. |
| Playwright screenshot capture against the live URL | The earlier `libasound.so.2` blocker is resolved; real Chromium now launches and captures real screenshots of the live public deployment (`artifacts/screenshots/tactical/`). Caveat below — the specific captures on file are of a non-live run. |

### Built and tested, but not yet integrated/enabled — real code, not yet exercised the way a demo narrative might imply

| What | State |
|------|-------|
| NetBird worker mesh | Wired into `worker_orchestrator.py` behind `NETBIRD_ENABLED` (real code, real tests: `test_netbird_gate.py`, 13 passed) — but `NETBIRD_ENABLED=false` in `.env.production`. It has never enrolled a real peer. Inert by flag, not by missing code. |
| GitHub-repo-as-investigation-input | Real heuristic scanner (`repo_scanner.py`: docker-compose/Dockerfile/K8s/Terraform/OpenAPI detection, provenance-tagged, confidence-capped), real tests, a working `POST /v1/investigations/intake` and intake screen. Its own code comment says it plainly: it "intentionally does not itself materialize the derived model into the 3D Multiverse view — that integration is a separate follow-up task." Does not feed the live provisioning/campaign pipeline yet. |
| Existing screenshot captures | Real screenshots, real browser — but captured from a run with `campaign.phase=FAILED`, `backend_cost_micros=0`, `reconciliation_status=PROVIDER_UNAVAILABLE`. Real captures of a non-real-infra run; not visual proof of the golden campaign. Re-capture needed once the gap below closes. |

### The single biggest remaining gap

**The real M20 golden campaign (`POST /v1/campaigns/golden`) triggering actual live Vultr worker creation
as part of one integrated run has never successfully completed.** Two live attempts on 2026-09-27 both
failed before producing a real completed round trip: one 500'd at the live-worker-listing step on an ACL
error; a later one returned HTTP 200 in 5.7 seconds but with `campaign.phase="FAILED"`,
`live_worker_outcome="not_attempted"`, and `live_provider="mock"` in its own timing block — i.e. a real
request against real infra that did not actually run a live worker. (An earlier draft of
`docs/milestones/M20_RELEASE_EVIDENCE.md` mischaracterized that second run as a successful ~4.5-minute
live campaign and its screenshots as "PASS ... live golden campaign"; both claims are corrected there and
in `docs/release/M20_REALITY_MATRIX.md` as of this pass.) This is the one thing that would demonstrate the
full advertised pipeline — twin → competing hypotheses → Director → Scheduler → disposable worlds →
evidence → counterexample search → remediation comparison → GhostShield-authorized teardown — as one real
run, rather than proven subsystems in isolation. Everything downstream of it (live SSE proof against a
real campaign, 24-frame UI acceptance against real data, TOUR-20) is still blocked on it.

---

## Agent 59 — claims review (summary)

| Claim | Verdict |
|-------|---------|
| "Autonomous investigation in controlled environments" | PARTIALLY_SUPPORTED |
| "Real Vultr workers in every demo" | UNSUPPORTED (mock default; live gated) |
| "Fully integrated causal + watch + runtime in one campaign" | UNSUPPORTED |
| "Production-ready SOC platform" | OVERSTATED → use RESEARCH_PROTOTYPE |
| "GhostArena qualifies release" | PARTIALLY_SUPPORTED (sim only) |

Unsupported claims removed/softened in README status section.

## Agent 60 decision: **NO-SHIP**

Triggers: no verified live golden path; GhostShield bypass; no runtime restart recovery in campaign; frontend not production-state-driven; no m20 screenshots; git has no baseline commit; full spec golden timeline not satisfied.

---

## What is GhostRange?

Evidence-grounded cyber digital-twin investigation: compile authorized input, hypothesize, experiment, verify, optionally act through GhostShield, audit via GhostLedger, improve via GhostEvolve, qualify via GhostArena.

## Canonical campaign flow

`POST /v1/campaigns/golden` — see `docs/architecture/GHOSTRANGE_FINAL_ARCHITECTURE.md`.

## Golden campaign (mock, verified)

- **Input:** `ranges/.../docker-compose.yml` (machine-readable).
- **Hypotheses:** 3 (middleware, identity cache, gateway routing); hidden true mechanism `session_refresh_cache`.
- **Workers:** 0 in mock path; `owned_workers: []`.
- **Arena:** QUALIFIED (sim).
- **Cost:** $0 mock.

## Live campaign

**ATTEMPTED TWICE, NOT YET SUCCESSFUL** — requires `ALLOW_M20_LIVE_CAMPAIGN=true`, Vultr ACL, VPC,
Postgres worker store. Both live attempts on 2026-09-27 failed before a real live worker ran (one 500'd on
ACL at worker-listing; one returned HTTP 200 in 5.7s with `phase="FAILED"`, `live_provider="mock"`). See
"The single biggest remaining gap" above.

## Vultr services used (when configured)

| Service | Role |
|---------|------|
| Cloud Compute | Control VM + ephemeral workers; one full single-worker lifecycle proven REAL_LIVE 2026-09-27 (create→bootstrap→benchmark→artifact→teardown→confirmed-destroyed), not yet proven as part of a golden-campaign run |
| Managed PostgreSQL | Events, worker leases |
| Object Storage | Artifacts |
| Serverless Inference | Director/analyze smoke; **+ real concurrent worker pool** (`inference_worker_pool.py`, `/v1/scheduler/inference-workers/dispatch`) — up to 10 concurrent real calls, GhostShield-mediated, hard-capped at `MAX_ACTIVE_INFERENCE_WORKERS<=10` / `INFERENCE_WORKER_MAX_USD<=$25` per session (real VM compute concurrency is capped separately at `MAX_ACTIVE_COMPUTE_WORKERS<=1`, split from the inference cap 2026-09-27 so one config change can't accidentally raise real-VM concurrency); verified REAL_LIVE 2026-09-27 (see M20_REALITY_MATRIX.md) |

## What remains simulated

Director observations, adversarial search, Arena ranges, default worker path, much of UI replay.

## Enterprise deployment would require

Multi-tenant isolation, auth/IAM, Shield bypass closure, live Arena, formal backup/restore drills, SOC integrations.

## Commands

```bash
scripts/m20-release-check.sh
scripts/m20-golden-path.sh   # mock against local API
ALLOW_M20_LIVE_CAMPAIGN=true M20_LIVE_CAMPAIGN_MAX_USD=15 scripts/m20-golden-path.sh
```

---

**GhostRange does not ask an AI what is wrong and trust the answer** — but M20 **does not yet SHIP** as a complete production proof of every bullet in the vision deck.
