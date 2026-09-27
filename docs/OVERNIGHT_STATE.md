# GhostRange Overnight Campaign State

**Update (2026-09-27, later same day):** blocker #2 below (Vultr Compute ACL rejecting this runner) was worked around by running from the control VM itself — a real end-to-end single-worker lifecycle (create/bootstrap/benchmark/teardown/confirmed-destroyed) has since been proven; see `docs/milestones/M2_CHECKPOINT_2026-09-27.md` and `docs/milestones/M20_FINAL.md`. The golden-campaign-triggered live worker (as one integrated run) still has not completed — that remains the real, current gap.
**Snapshot:** 2026-09-27 09:55 UTC  
**Campaign mode:** lead-coordinated local execution; six parallel audit workstreams in Wave 0  
**Final recommendation so far:** `NO-SHIP`

## Current objective

Advance GhostRange toward a truthful, integrated, demonstrable release without changing the locked product idea, creating unsafe cloud resources, publishing secrets, triggering GitHub Actions, or claiming simulated behavior is live.

## Locked product idea

GhostRange is an evidence-grounded cyber-defense proving ground. It reconstructs authorized systems in disposable environments, forms competing incident explanations, runs controlled experiments, tests remediations and counterexamples, preserves evidence/provenance, and leaves consequential production authority with humans.

## Locked architectural rules

- GhostDirector decides **what** to test; GhostScheduler decides **how** approved work executes.
- The control plane retains provider authority; workers must not receive the main `VULTR_API_KEY`.
- GhostShield and typed execution gateways mediate consequential effects.
- Mock, simulated, controlled-live, and real-live execution modes remain distinct.
- Evidence must carry provenance and limitations; a model proposal is not verification.
- Vultr remains the intended disposable compute substrate, but live Compute actions are explicit, bounded, and billable.

## Locked UI rules

- Exactly three primary modes: `MULTIVERSE`, `EXECUTION`, and `EVIDENCE`.
- One spatial tactical experience; no permanent left navigation sidebar.
- 3D communicates topology, worlds, workers, DAGs, and relationships; DOM communicates readable text, numbers, logs, forms, and accessibility.
- The frontend must label `LIVE`, `SIMULATED`, `HISTORY`, `FIXTURE`, and offline states truthfully.

## Wave 0 audit outputs

| Workstream | Result |
| --- | --- |
| Repository / milestones | M20 is explicitly `RESEARCH_PROTOTYPE` / `NO-SHIP`; the public GitHub repository and follow-up baseline are published. |
| Backend / API / events | Local campaign, cost, timing, worker, SSE, Shield, Director, Scheduler, Ledger, and evidence routes exist; current M20 campaign is mock-first and several routes are absent from the deployed build. |
| Frontend / 3D UI | Three modes are implemented; live/replay/fixture semantics are explicit; timing/cost/evidence panels exist; screenshot acceptance is still UI-NO-GO pending human review and capture environment. |
| Infrastructure / deployment | HTTPS UI and `/health/ready` are reachable; deployed API is stale; no new billable resource was created. |
| Cost / timing / scheduler | Integer microdollar ledger, one-hour Compute quantum, inference token costing, budget reservations, Postgres persistence hooks, and percentile timing store exist; provider invoice reconciliation is honest about API limitations. |
| Security / release | Secret scan is clean for repository content; ignored local credentials exist and remain outside publication; provider ownership and Shield tests pass; live worker proof remains blocked by Vultr API ACL. |

## Current verified test status

- `make demo`: 6 passed.
- `bash scripts/m20-release-check.sh`: 492 Python tests passed, 9 skipped; 21 M16–M19 package tests passed; 26 frontend tests passed; typecheck passed; mock campaign passed; Arena simulator qualified.
- `pytest -q apps/api/tests/test_netbird_gate.py`: 13 passed.
- README internal links: 23 checked, none missing; Mermaid blocks: 7.
- Public HTTPS deployment: HTTP 200; `/health` and `/health/ready` return 200.

## Known blockers

1. Public deployment is stale relative to this checkout; current campaign and newer subsystem routes return 404 there.
2. Vultr Compute API ACL rejects this runner's egress IP; no live worker was created.
3. NetBird enrollment/readiness/revocation is now wired into the live worker orchestrator behind `NETBIRD_ENABLED`; it remains unverified against a real account.
4. Screenshot/tour acceptance requires a compatible browser runtime and human review; the prior capture attempt lacked `libasound.so.2`.
5. The repository contains an ignored local `.env` with configured credentials and an ignored `vultr` OpenSSH private key. Neither is tracked, but neither may enter a public commit.

## Decisions made in this campaign

- Added root `pytest.ini` `asyncio_mode = auto` because the root config overrode package config and caused six async tests to be rejected.
- Added `test-results/` and `playwright-report/` to `.gitignore`.
- Replaced the root README with an evidence-grounded product, architecture, operations, security, cost, and maturity guide.
- Did not delete or alter local credentials/keys; they are a human-managed external-secret concern.
- Did not create live Vultr resources, force-push, or trigger GitHub Actions. The approved remote is `https://github.com/chetas1208/GhostRange.git`.

## Highest-value next work

1. Deploy the current checkout to the control VM through the approved deployment path, then re-run health and route checks.
2. From the ACL-allowed control VM, run exactly one bounded CPU worker lifecycle only if human authorization remains valid; prove `owned_workers == []`.
3. Run a durable restart test against local PostgreSQL for campaign cost and timing state.
4. Run screenshot capture in a supported container/browser environment and complete the existing 24-frame human acceptance.
5. Review the published repository, then address the remaining external release gates.

## Human action required

- Review the initial public GitHub repository and commit contents.
- Decide whether the ignored `.env`, SSH key, and any associated access credentials should be rotated or retained outside the repository.
- Authorize a current control-VM deployment and, separately, one billable CPU worker lifecycle if live proof is required.
- Review the 24-frame tactical UI/tour acceptance.

## Independent review wave

| Reviewer | Result |
| --- | --- |
| Product truth | `GO` — README and local campaign describe the implemented mock/simulated boundaries honestly. |
| Architecture | `GO` — Director/Scheduler split, control/data plane, lifecycle, and Shield boundaries are present. |
| Security | `GO` — targeted Shield/ownership/cap tests pass; dry-run candidate scan found no credential patterns. |
| Cost / Scheduler | `GO` — 136 targeted package tests pass; integer microdollars and billing-quantum logic are covered. |
| UI / UX | `GO` — exactly three primary modes and truthful execution labels are present; visual sign-off remains human-gated. |
| Release / Documentation | `NO-GO` — external deployment, live worker proof, and human visual gates remain open; initial publication is complete. |
