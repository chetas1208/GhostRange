# ADR-M2: Range Provisioning for `ghostrange-auth-lab-v1`

Status: Accepted (Agent 03, Infrastructure / Range Provisioning Engineer, M2 wave 1,
2026-09-26). Depends on: Decisions.md #7, #9, #12; ADR-006-vultr-integration.md;
docs/research/VULTR.md. Owns: `infra/`, `packages/range-iac/`,
`ranges/ghostrange-auth-lab-v1/`.

## Context

M2's job for this role is to turn a `RangeSpecV1` into real, reproducible Vultr
infrastructure for exactly one canonical range: `ghostrange-auth-lab-v1`, a 4-tier
chain (gateway → api → auth → data store) fronted by the internet/a test origin.
ADR-006 already established the Vultr-side facts this decision has to respect:

- There is no literal "instance template" object — Vultr's create-instance call is a
  composable request (`os_id`/`snapshot_id` + `script_id`/`user_data` + `vpc_ids` +
  `firewall_group_id`).
- Snapshot creation takes 20–30 minutes and must never be on the critical path of
  provisioning or forking a world.
- `packages/vultr-control` is the single intended choke point for all Vultr API
  calls (ADR-006 Consequences).
- Range assets are plain Compute instances, never VKE (Decisions.md #11 / ADR-006).

What ADR-006 left open, and this ADR resolves for the concrete `range-iac` compiler:
how a `RangeSpec` actually becomes instance-create calls; whether that's expressed as
OpenTofu HCL (per Decisions.md #7) or something else; what the boot-time image
strategy is (bare OS + cloud-init vs. a custom Packer image vs. Vultr snapshot); and
how the LOGICAL/PHYSICAL split this M2 task explicitly demands gets represented when
`ghostrange_contracts.RangeSpecV1` has no placement or reachability-edge field at all.

## Decision

1. **A new, `range-iac`-owned model family (`RangeTopologyPlanV1`) carries
   everything `RangeSpecV1` doesn't: physical placement and reachability edges.**
   `RangeSpecV1` (frozen for M2 wave 1) has no field for "which VM does this asset
   run on" or "what can reach what" — only `networks`/`assets`/`policy_id`/`budget_id`.
   Rather than propose breaking changes to a frozen contract for a need that is
   specific to this compiler, `packages/range-iac/ghostrange_range_iac/models.py`
   defines `RangeTopologyPlanV1`/`PhysicalGroupV1`/`ReachabilityEdgeV1` as a
   companion, versioned-the-same-way file checked in next to the RangeSpec
   (`ranges/<name>/topology.yaml`). This is proposed here, per the M2
   contract-change protocol, as an **additive candidate** for `ghostrange_contracts`
   later, not adopted into it silently now.
2. **Range asset compilation targets direct Vultr API request objects consumed via a
   provider interface, not generated OpenTofu HCL** — see "OpenTofu vs. direct
   compilation" below. This narrows Decisions.md #7's OpenTofu choice specifically
   for range-asset compilation; it does not repeal it for other future
   infrastructure.
3. **Boot-time strategy: cloud-init on a bare `os_id`, with an explicit two-mode
   compiler (`mode="base"` / `mode="fork"`), no custom Packer image for M2** — see
   "Image strategy" below.
4. **One VPC 2.0 per range, one Firewall Group per range; a firewall rule is only
   compiled for an edge that crosses a physical-group boundary or originates at a new
   `INTERNET` sentinel** — same-host edges (both ends on the same physical VM) are
   docker-compose's problem, not Vultr's. This is the concrete mechanism by which
   `packages/range-iac` keeps LOGICAL topology (the RangeSpec) and PHYSICAL placement
   (the topology plan) genuinely separable: the same RangeSpec compiles to zero or
   many real firewall rules purely depending on the topology plan it's paired with.
5. For `ghostrange-auth-lab-v1` specifically: **one physical group (`vm-1`) hosts all
   four logical assets** (gateway/api/auth/data-store) via docker-compose, per the M2
   task's "simplest thing that's honest and reproducible" guidance. Only the
   `INTERNET → gw01` edge compiles to a real firewall rule; the other three
   (gw01→api01, api01→auth01, auth01→db01) are same-host for this layout.

## Alternatives considered

### Compilation target: instance template vs. direct create-instance vs. OpenTofu

- **A single "instance template" resource.** Not available — ADR-006 already
  established Vultr has no such object; rejected as a non-option, not a real
  alternative.
- **Generate OpenTofu HCL (`vultr_instance`/`vultr_vpc2`/`vultr_firewall_group`),
  per Decisions.md #7.** This is the project's own prior locked choice, and it's not
  wrong in general — it's a real, working pattern (ADR-006's own field-mapping table
  was written with `vultr_instance`'s Terraform schema, and that mapping is reused
  unchanged in `provider_interface.py`'s request shapes). Rejected specifically for
  *this* compiler's output because:
  - ADR-006's own Consequences section commits to `packages/vultr-control` being the
    **single, mockable choke point** for every Vultr API call, explicitly so that
    Decisions.md #9's safety boundary (range-ownership tokens, policy-check gating)
    has exactly one place to enforce from. A Terraform/OpenTofu run using the Vultr
    provider talks to the Vultr API **directly**, with its own credentials, its own
    state file, completely outside that choke point. Two live paths to the same
    Vultr account is a second attack surface Decisions.md #9 was written to avoid,
    not a detail.
  - GhostRange's create/destroy/fork pattern is not "a human periodically runs
    `tofu apply` against slowly-changing infrastructure" — it's GhostScheduler
    programmatically creating and tearing down whole worlds, potentially many in
    parallel, at a pace bounded by Vultr's ~30 req/s rate limit (ADR-006 §4). That's
    a request-queue/backoff problem, which `packages/vultr-control` already has to
    solve for its own sake; running that same logic *underneath* a Terraform
    provider plugin, and separately reasoning about Terraform's own state-locking and
    plan/diff semantics on top, is two abstractions solving overlapping problems.
  - OpenTofu's plan/diff workflow is a genuine advantage for hand-managed,
    long-lived infrastructure where a human reviews a diff before it's applied.
    Disposable, forked-per-investigation range assets are the opposite of that
    profile.
  - This is a **narrowing**, not a repeal, of Decisions.md #7: OpenTofu remains a
    plausible fit for infrastructure that *is* long-lived and hand-managed (ADR-006
    flags the orchestration/worker fleet as the candidate), which is exactly why
    `infra/` is left intentionally empty rather than deleted or repurposed — see
    `infra/README.md`.
  - **Call made by this agent; flagged for lead-agent reconciliation** per the M2
    contract-change protocol, since it touches a Decisions.md-locked choice, not just
    an open question.
- **Direct Vultr API request objects via a `VultrProviderProtocol`** (what was
  built). Adopted: keeps `packages/vultr-control` as the single choke point,
  composes with the rate-limit/backoff/safety-boundary machinery that already has to
  live there regardless, and produces a compiler whose output (`CompiledRangeInfra`)
  is pure data, trivially unit-testable with zero external dependencies (see
  `packages/range-iac/tests/`).

### Image strategy: bare OS + cloud-init vs. custom Packer image vs. Vultr snapshot

- **Custom Packer-built image (pre-baked with Docker + pulled images), used from the
  first boot.** Real option, not a strawman — Vultr does have a Packer plugin.
  Rejected **for M2 specifically**, not in general: `ghostrange-auth-lab-v1`'s
  docker-compose content (`docker/vm-1/`) is an explicit, documented placeholder —
  the wave-2 "controlled scenario" agent is expected to replace it with the real
  vulnerable application. Baking a Packer image now means re-baking (a separate build
  pipeline, versioning, and its own wall-clock cost) every time that content changes
  during active scenario development — the wrong trade while the thing being baked is
  still churning. **DEFER, not reject**: once scenario content stabilizes, a Packer
  (or equivalent) base image that pre-installs Docker (skipping the ~10-minute
  cloud-init docker-install step on every future *base* materialization) becomes a
  reasonable optimization — revisit if base-image rebuild frequency stays low enough
  that the one-time bake cost is worth it.
- **Cloud-init on a bare `os_id`, every boot, no snapshot at all.** This is the naive
  version of what was built, and it's wrong on its own for the *fork* path
  specifically: Vultr's own docs put cloud-init's first-boot processing at roughly 10
  minutes (docs/research/VULTR.md §4). Paying that on every fork of a world would
  directly violate Decisions.md #12 ("world-fork must use pre-warmed golden
  snapshots, never snapshot-on-critical-path") by making *forking itself* slow, even
  though no new snapshot is being created at fork time.
- **What was actually built: cloud-init on a bare `os_id` for `mode="base"` (pays the
  ~10-minute cost once, while materializing the golden copy of a world), and a
  separate, lighter `mode="fork"` cloud-init that assumes Docker + images are already
  present (restored from a pre-existing snapshot) and only re-asserts the compose
  file and runs `docker compose up -d`.** This is the two-compilation-mode design
  ADR-006's Consequences section already anticipated as necessary and is what
  `compiler.py`/`cloud_init.py` implement. The golden snapshot itself is never
  created by this compiler — `compile_range(..., mode="fork", snapshot_map=...)`
  only ever *consumes* a snapshot id that was produced out of band, consistent with
  Decisions.md #12.

## Tradeoffs

- Direct-provider compilation is faster to iterate and test (no Tofu binary, no
  state backend, pure-Python unit tests) but forfeits Terraform/OpenTofu's
  plan/diff-before-apply safety net and its large existing ecosystem of drift
  detection. Given range assets are disposable and created/destroyed by code, not by
  a human reviewing a plan, this is judged to cost less than it saves for this
  specific use.
- Consolidating all four logical assets onto one physical VM for M2 is cheap and
  simple, but it means the `INTERNET → gw01` edge is the *only* edge this canonical
  range currently exercises the real Vultr firewall-rule-compilation path for — the
  cross-physical-host case is proven correct only by a synthetic fixture
  (`test_cross_host_edge_compiles_to_a_firewall_rule` in
  `packages/range-iac/tests/test_compiler.py`), not by the real range. Accepted for
  M2; a future topology.yaml for this same range that actually spans multiple VMs
  would be the real-world confirmation.
- A one-VM-per-range layout also means this range's four "tiers" share fault domains
  and a resource pool at the OS level — a container OOM-killing another container's
  neighbor is possible in a way it wouldn't be across separate VMs. Acceptable for a
  disposable investigation range where the goal is reproducing a topology's request
  flow and reachability, not resource isolation guarantees.
- `RangeTopologyPlanV1` living outside `ghostrange_contracts` avoids destabilizing a
  frozen M2 wave-1 contract, but means two files (`rangespec.yaml` + `topology.yaml`)
  must be cross-validated by hand (or by the compiler's own checks) rather than by a
  single schema. `compiler.py`'s `_validate_placement`/`_compile_edges` do this
  cross-validation explicitly and raise `TopologyMismatchError` on any drift (asset
  placed twice, asset never placed, unknown hostname in an edge, declared vs. derived
  `needs_public_ip` disagreement) rather than silently producing wrong infrastructure.

## Security implications

- **VPC 2.0 per range, not a shared VPC.** Per ADR-006, this is the architectural
  (network-fabric-level) isolation boundary between sibling/forked worlds, and it is
  applied here even though M2's single range currently has only one physical
  instance in it — the boundary exists for when a sibling world (a fork of this
  range, or an unrelated range) is provisioned alongside it, not because this range
  alone needs isolation from itself.
- **Default-deny, explicit-allow firewall compilation.** Only edges the RangeSpec
  author actually declared produce a rule; nothing is opened "just in case." The one
  compiled rule for `ghostrange-auth-lab-v1` (`INTERNET → gw01:80/tcp`) is scoped to
  exactly that port/protocol, not a blanket allow.
- **No operator/SSH access is compiled by this ADR's scope.** `InstanceCreateRequest`
  has no firewall rule for port 22 anywhere in this design — deliberately left as
  future work rather than defaulting to an open or hardcoded-CIDR SSH rule, since
  getting that wrong (e.g. `0.0.0.0/0` on 22) is a worse failure mode than not
  addressing it yet. Whoever wires operator access should route it through
  Decisions.md #9's range-ownership-token model, not a bare firewall rule.
- **Direct-provider compilation keeps `packages/vultr-control` as the sole holder of
  Vultr credentials** (see "OpenTofu vs. direct compilation" above) — this is itself
  a security property, not just an architectural preference: one centralized place
  to add the range-ownership-token/allowlist check Decisions.md #9 requires, instead
  of two (vultr-control's own client, plus whatever holds the Terraform provider's
  credentials).
- **Lab credentials are obviously fake and never leave the disposable world.**
  `docker/vm-1/files/data-store/init.sql` and `auth/app.py` use a clearly-labeled
  placeholder credential (`demo` / `ghostrange-lab-only`), and the data store
  container publishes no host port — it is reachable only from `auth01` over
  docker-compose's own bridge network, never from the gateway or the internet.

## Reproducibility

- Every artifact needed to reconstruct this range's infrastructure from scratch is a
  checked-in file: `rangespec.yaml`, `topology.yaml`, `docker/vm-1/docker-compose.yml`,
  and its support files. `compile_range(...)` is a pure function of these inputs —
  running it twice on the same files produces byte-identical `CompiledRangeInfra`
  output (proven by the deterministic test suite, not just asserted).
  `packages/range-iac/tests/test_rangespec_validates.py` additionally proves the
  RangeSpec round-trips through `model_dump`/`model_validate` unchanged, and
  `test_rangespec_validates.py`/`test_topology.py` prove both files parse and
  cross-validate against the real Pydantic models, not a hand-maintained copy of
  their shape.
- No step in provisioning this range depends on manual console configuration:
  everything Vultr needs (VPC subnet, firewall rules, instance plan/region/image,
  full application boot sequence) is either in `topology.yaml` or in the cloud-init
  `user_data` the compiler renders — see `render_cloud_init` in `cloud_init.py`.
- The one non-reproducible-by-this-repo-alone step is the golden snapshot itself
  (`mode="fork"`'s `snapshot_map`): a snapshot id is an opaque Vultr resource that
  exists only after a real `mode="base"` instance has been provisioned, reached
  steady state, and been snapshotted out of band (20–30 minutes, per ADR-006) by
  whatever runtime component drives that workflow (`packages/range-runtime`, per
  M2_COORDINATION's ownership table — outside this deliverable's scope). This ADR's
  compiler only ever *consumes* that id; it is not itself a source of
  non-reproducibility, but it is a real dependency worth naming.

## Teardown behavior

- **No instance-level backups are requested** (`InstanceCreateRequest` never sets
  Vultr's `backups`/`backups_schedule`) — consistent with ADR-006's Consequences
  section: range assets are disposable by design, and durability lives in the
  evidence layer (Object Storage, per `docs/research/VULTR.md` §7), not in
  keeping a compromised/attacked instance's disk state around.
- **Teardown order is the mirror of `apply.py`'s creation order**, and matters for
  the same reason creation order does: instances must be terminated before the
  firewall group and VPC they reference, or the provider will reject the
  delete (a firewall group / VPC with dependents attached cannot be removed cleanly
  on Vultr). `apply.py` intentionally does not implement teardown itself — that
  belongs to whichever runtime component owns a `Range`'s `STOPPING`/`DESTROYING`
  lifecycle transition (`packages/range-runtime`, per
  `ghostrange_contracts.range.RANGE_LIFECYCLE_TRANSITIONS`) — but it is documented
  here so that component's implementer doesn't have to re-derive the ordering
  constraint: **instances first, then firewall rules/group, then VPC**, the exact
  reverse of `apply_compiled_infra`'s phases.
- **A `DESTROYED` range leaves nothing billable behind** if teardown completes: no
  snapshot is implicitly retained by this compiler (a golden snapshot used for
  `mode="fork"` is a separate, deliberately-kept resource with its own lifecycle,
  not an artifact of tearing down any one forked instance). Evidence that must
  outlive the range (per ADR-006 §7) is expected to have already been shipped to
  Object Storage by the evidence layer before teardown — this compiler has no
  opinion on when that happens, only that it isn't this compiler's job.
- **Partial-failure teardown is out of scope for this ADR's code** (e.g. an instance
  terminates but the firewall group delete then fails) — `apply_compiled_infra`
  has no rollback/retry logic today. Flagged explicitly as a gap for
  `packages/range-runtime`/the wave-3 "failure/cleanup/reconciliation" owner
  (M2_COORDINATION item 16) to close, rather than silently assumed away.

## Consequences

- `packages/vultr-control`, once it lands, needs to satisfy (or be thinly adapted to)
  `provider_interface.VultrProviderProtocol` — see that file's reconciliation note.
- `RangeTopologyPlanV1` is proposed, not merged, into `ghostrange_contracts` — the
  lead agent should decide whether GhostScheduler's own physical-placement needs
  (M2_COORDINATION's flagged `ComputeResourceV1` gap) end up subsuming it, replacing
  it, or leaving it as range-iac-local permanently.
- Any other range added after `ghostrange-auth-lab-v1` should follow the same
  `rangespec.yaml` + `topology.yaml` + `docker/<group>/...` convention documented in
  `packages/range-iac/README.md`, so the compiler needs no per-range special-casing.
