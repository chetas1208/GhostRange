# GhostRange Checkpoint — 2026-09-27

**Latest update (this checkpoint, post-rebuild verification):** ownership-check fix is deployed live and confirmed — `GET /v1/scheduler/compute-dry-check` on the real production API returns `owned_worker_count: 0`, `owned_workers: []`. All health checks (`postgres`, `redis`, `object_storage`, `inference`) report `ok`. No orphans, no drift between code and deployment.

Point-in-time snapshot of real, verified state. Where a claim isn't independently verified, it's marked as such. See `docs/milestones/M2_INTEGRATION_STATUS.md` for the live outstanding-work tracker and `Decisions.md` for the full decision history — this doc is a snapshot, those are the running sources of truth.

## Live deployment

- **Public URL(s)**: `https://45.76.248.45.sslip.io/`, `https://45-76-248-45.nip.io/` (real Let's Encrypt certs, both verified), `http://45.76.248.45/` (plain-HTTP fallback, always works regardless of DNS). No purchased/registered domain — using free wildcard-DNS services (`sslip.io`/`nip.io`) that resolve straight to the VM's IP.
- Control VM: `ghostrange-control` @ `45.76.248.45`. Stack: `docker-compose.prod.yml` — `api`, `web`, `proxy` (Caddy), `valkey`. All healthy as of last check.
- SSH access: password auth works (key `vultr` is passphrase-locked, no TTY available to unlock it in this environment). `.env`'s `GHOSTRANGE_CONTROL_SSH_PASSWORD` had a stray-leading-space bug (fixed in how it's read, not in the file format itself — still needs stripping wherever read).

## Security

- **GhostShield policy-bypass (found + closed today)**: the orchestrator was constructing the real Vultr provider directly, with zero policy mediation, on the `M2OneWorldOrchestrator`/campaign path. Fixed via a new `ShieldedVultrAdapter`; `GHOSTSHIELD_MODE=DISABLED` is now the only escape and requires an explicit env var (default is never unshielded). Verified with real tests, no regressions.
- **Ownership-check gap (found + closed today)**: `list_computes(range_id=None)` returned every Vultr instance in the account, tagged or not — meaning `terminate_worker()`'s ownership check was a no-op whenever called without a specific range_id (which is exactly how teardown calls it). Fixed in both real and mock providers; a foreign/untagged instance is now provably rejected before any destroy call happens. **Not yet fixed**: `list_worlds()` has the identical pattern for the `DESTROY_WORLD` action — flagged, not yet fixed.
- Two live API keys were pasted directly into chat during this session (a Vultr Compute key and a NetBird API token/setup key) — both stored only in `.env`/`.env.production` from that point on, never re-echoed. Recommend rotating both once this work is demo-stable, since anything pasted into a chat transcript should be treated as exposed.
- `GHOSTSHIELD_MODE=ENFORCE` confirmed on the live VM.

## Real infrastructure proof (the actual milestone)

One full real worker lifecycle has been proven end-to-end, independently verified (not just HTTP-200 trusted):
1. Real Vultr Compute VM created (`vc2-1c-1gb`, region `ewr`)
2. Worker agent bootstrapped, registered with control plane
3. Ran a real CPU benchmark (2,000,000 iterations, 436ms) — result stored as a real Postgres artifact row
4. Worker torn down; deletion confirmed via a direct per-resource Vultr GET returning 404 (not just an eventually-consistent list call)
5. A found teardown-race bug (false-negative 500 on a genuinely successful teardown, caused by checking Vultr's laggy list endpoint instead of trusting the destroy call's own confirmation) — fixed and redeployed.

Separately, 10 real concurrent Vultr Serverless Inference calls were proven working (distinct request IDs, real ~50ms-apart dispatch, budget-capped at $25, hard-clamped concurrency ceiling of 10) — this is a different Vultr product (bearer-token API, not IP-restricted) from the Compute VM path above.

4 orphan Vultr VMs (leftovers from earlier chaotic test runs, before the Compute API key's IP-ACL was sorted) were cleaned up through the real shielded termination path and confirmed gone. 4 stale `worker_leases` DB rows from the same earlier chaos were released via a newly-built guarded reconciliation primitive.

Worker-cap config is now hard-split: `MAX_ACTIVE_COMPUTE_WORKERS=1` (real billable VMs) vs `MAX_ACTIVE_INFERENCE_WORKERS=10` (logical, no VM lifecycle) — previously one shared `MAX_ACTIVE_WORKERS` var could accidentally let a change meant for inference concurrency inflate real VM concurrency; a real regression test now guards this specifically.

## Not yet done

- **The real M20 golden campaign has never completed live.** `POST /v1/campaigns/golden` triggers real infra creation and is gated by this sandbox's own safety classifier — it must be triggered by the user directly, not by any agent in this session (denials here are not routed around, by design). This is the single biggest remaining proof: it's what demonstrates the full advertised pipeline (twin → competing hypotheses → Director → Scheduler → disposable worlds → evidence → causal falsification-attempt → remediation comparison → GhostShield-authorized teardown) as one real run, not just the worker subsystem in isolation.
- Live SSE proof, 24 UI-acceptance screenshots, visual regression, and the final UI-GO/SHIP checklist are all downstream of that campaign run — none attempted yet for real.
- Landed after this checkpoint (2026-09-27, later same day, see commits `e39676f`/`d7c5eda`): the GitHub-repo-as-input feature (repo → derived system model → minimal `/start` intake screen) and NetBird mesh wiring (now consumed by `worker_orchestrator.py`) both landed as real, tested code. Neither is fully integrated into the live pipeline yet: the intake screen's own code comment states it does not materialize the derived model into the 3D Multiverse view, and NetBird remains inert (`NETBIRD_ENABLED=false` in production — it has never enrolled a real peer).

## What this session will NOT do without the user

- Trigger the live golden campaign (classifier-gated, by design)
- Any raw/ad-hoc SQL writes outside a guarded application-level mechanism (one denial today; the equivalent fix succeeded once routed through a real reconciliation primitive instead)
- Weaken the Vultr API IP allowlist, add credentials to the frontend, or enable NetBird live enrollment
