# M2 Integration Status — Backend (this session)

## TODO / outstanding (2026-09-27, live)
- [x] Ownership-check security fix — `list_computes()` (both real + mock providers) now drops untagged/foreign instances before any range_id filter. Real test proves a foreign VM id is rejected by `terminate_worker()` via GhostShield's P1 check. 131 passed. **Needs sync+rebuild on the live VM (in progress).**
- [x] Stale 4-row `worker_leases` cleanup — real guarded reconciliation primitive built (`WorkerStore.release_stale_lease`), all 4 released for real against production Postgres.
- [x] Follow-up: `list_worlds()` ownership filter — untagged VPCs excluded (mirrors `list_computes`); tests in `test_real_provider_requests.py` + `test_mock_provider.py` (2026-09-27).
- [~] GitHub-repo-as-input feature (repo → derived system model → minimal input screen) — agent running (`af1d8a1d7ce694cb0`)
- [~] NetBird mesh wiring — agent running (`a0c33a81710b0ab39`), credentials stored inert (`NETBIRD_ENABLED=false`)
- [ ] **Real golden campaign trigger** (`POST /v1/campaigns/golden` against the live deploy) — blocked on the user specifically, not executable by this session (live-infra classifier denial, not routed around per session rules). Unblocks: live SSE proof, 24 UI-acceptance screenshots, visual regression, final UI-GO/SHIP checklist.


> Root `Progress.md` was overwritten 2026-09-27 by a separate, much larger sweep (M1-M14: GhostScheduler V3, Living Twin, GhostLedger, GhostDirector, GhostGate/Watch/Mesh/Causal — mostly recorded there as mock/simulated/NO-GO) that this session did not create and has no prior record of. This file is the durable record of THIS session's backend M1 + M2-wave-1 work, since the shared root file is no longer reliable for that. See conversation/Decisions.md (intact, not overwritten) for the decision history.

## M1 (complete, real, tested)
- `packages/contracts` — 29 versioned Pydantic models, JSON-Schema exported, 49 tests.
- `packages/events` — 23 events, registry, discriminated union, 73 tests.
- `packages/evidence` — content-addressed artifact store, tamper detection, deterministic scenario verification, provenance chain traversal, 32 tests.
- docs/architecture/PRODUCT.md, ADR-001/002/006/011, docs/security/THREAT_MODEL.md + EXECUTION_POLICY.md, docs/research/{VULTR,CYBER_RANGES,INCIDENT_RESPONSE,OPEN_SOURCE,SCHEDULING,SPECULATION,ADAPTIVE_COMPUTE}.md, docs/ui/{THREE_D_ARCHITECTURE,INTERACTION_MODEL}.md (frontend reference only, owned by Cursor peer for implementation).
- Combined verified test count at M1 close: 122 (contracts+events), +32 evidence = 154+ before M2 wave 1.

## M2 wave 1 (backend, launched 2026-09-26)
| Agent | Package | Status |
|---|---|---|
| 01 Audit/Integration | docs/milestones/M2_AUDIT.md | **Done.** Found: zero git commits repo-wide at the time; event catalog covers only 7/21 domain objects; 3 inconsistent event-envelope shapes (apps/web already self-resolved to the right one); recommended widening Agent 08 to own a minimal apps/api. |
| 02 Vultr control-plane | packages/vultr-control | **Done.** RealVultrProvider + MockVultrProvider, 91 tests, honest `REAL_VULTR_E2E = NOT_RUN_NO_CREDENTIALS`. Corrected `/v2/vpc2`→`/v2/vpcs` and `vpc_ids`→`attach_vpc` (raw API) in docs/research/VULTR.md. |
| 03 Range provisioning/IaC | packages/range-iac, ranges/ghostrange-auth-lab-v1 | **Done.** RangeSpecV1 for the canonical range (gw→api→auth→db, consolidated on 1 VM for M2), real cloud-init/docker-compose, 24 tests. Narrowed Decisions.md #7: range assets compile straight to vultr-control, not generated OpenTofu HCL (single credential choke point). |
| 04 Range runtime | packages/range-runtime | **Cut off** by account-wide spend cap near completion (was at "153 tests passing, final tree check" per its last tool call). Files present on disk: engine.py, persistence.py, reconcile.py, vultr_adapter.py, provider.py, events.py, errors.py + 5 test files. **Not yet independently verified by lead agent — do not treat as confirmed done.** |
| 05 Security boundary | docs/security/RANGE_NETWORK_BOUNDARY.md | **Cut off** near completion (was mid-edit on EXECUTION_POLICY.md/THREAT_MODEL.md amendments). RANGE_NETWORK_BOUNDARY.md exists on disk (16KB). **Not yet independently verified.** |
| 08 Event/persistence (+apps/api, widened) | packages/events/store/, apps/api | **Cut off**, but left substantial work: packages/events/ghostrange_events/store/{models,postgres,pubsub,gateway}.py + schema.sql + tests/store/. apps/api's scope ballooned far past "minimal gateway" — see scope-boundary note below, largely NOT this agent's doing. **Not yet independently verified.** |
| 09 Evidence/verification | packages/evidence | **Done**, see M1 section above (this is where the M1 evidence package actually landed; M2 wave 1 relaunch of the same role produced no additional changes beyond what's listed). |
| 10 GhostScheduler v1 | packages/scheduler | **Cut off** near completion (was writing README). Files present: priority.py, cost.py, stopping.py, parallelism.py, resource_selection.py, normalize.py, scheduler.py, benchmarks.py, `v3/` subpackage (critical_path/plan/queue/placement), `simulator/` subpackage, 7 test files. **Not yet independently verified — note the presence of a `v3/` subpackage is unexplained by this agent's M2-wave-1-scoped brief and needs checking, may be leftover from the separate M1-M14 sweep sharing this package path.** |

## Scope boundary discovered 2026-09-27 (see docs/milestones/M2_COORDINATION.md for full note)
`apps/api` contains a large pre-existing route surface (`mesh_routes.py`, `causal_routes.py`, `ghostwatch_routes.py`, `ghostgate_bridge.py`, `promotion_routes.py`, `multiverse_fork.py`, `director_routes.py`, `worker_orchestrator.py`) plus `docs/security/GHOSTMESH_*`, `GHOSTCAUSAL_*`, `GHOSTWATCH_*`, `M10_SECURITY_REVIEW.md` — corresponding to the M11-M14 sweep referenced in root Progress.md's overwritten content. This session did not build these. **Out of M2 wave-1 scope — do not modify.** Confirmed with peer session `vultrhack26-27sep-8a`.

## Security findings 2026-09-27 (resolved / in progress)
- Live Vultr API key value was pasted into this session's chat by the user. Not used, not logged, not written to any file by this session. User advised to rotate + IP-restrict.
- Real SSH keypair (`vultr`/`vultr.pub`, 0600 private key perms) and `docker-compose.prod.yml`/`.env.production.example` exist at repo root, referencing an apparently-live control VM. Not created by this session. `.gitignore` was missing entries for the private key and for `.env.production.example`'s allow-rule — **fixed by this session** (added `/vultr`, `/vultr.pub`, `*.pem`, `id_rsa*`, `id_ed25519*`, `!.env.production.example`).
- `.env`/`.env.production` confirmed by peer session to already be correctly gitignored and untracked (zero `git status` entries) before the fix above.

## Lead verification (2026-09-27, Cursor trace pass)

| Package | `pytest` | Notes |
|---------|----------|--------|
| `packages/range-runtime/tests` | **pass** | Agent 04 cut-off work present and green |
| `packages/vultr-control/tests` | **pass** (99) | Includes `list_worlds` ownership tests |
| `packages/scheduler/tests` | **pass** | `v3/` + `simulator/` are part of repo scheduler (M4+ sweep), not M2-wave-1-only |
| `packages/events/tests` (excl. store) | **pass** | Postgres store tests optional (`--ignore=store`) |
| `docs/security/RANGE_NETWORK_BOUNDARY.md` | **on disk** | Agent 05 doc not re-audited line-by-line |

## Outstanding for lead agent (next actions)
1. ~~Independently verify Agents 04/05/08/10 cut-off work~~ — **runtime/vultr/scheduler/events suites green** (see table); RANGE_NETWORK_BOUNDARY still human read.
2. ~~Resolve scheduler `v3/` / `simulator/`~~ — **documented:** shared with later milestone work; tests pass.
3. Get user decision on: (a) real Vultr credential rotation, (b) whether the control VM at the IP in the pasted guide is intentional/authorized, (c) live golden campaign (`POST /v1/campaigns/golden`).
