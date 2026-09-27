# ghostrange-vultr-control

The single choke point for every call GhostRange makes to the Vultr API.
Per ADR-006 / `docs/research/VULTR.md` / `docs/milestones/M2_COORDINATION.md`:
**no other package talks to Vultr directly.** `packages/range-runtime` and
`packages/range-iac` depend on this package's interface, not on Vultr's SDK
or REST API directly.

Two implementations of one interface:

- **`RealVultrProvider`** — calls the actual Vultr API v2
  (`https://api.vultr.com`), authenticated with a real API key read from the
  `VULTR_API_KEY` environment variable.
- **`MockVultrProvider`** — deterministic in-memory fake, for unit tests,
  offline dev, and frontend dev with no live Vultr account. Every record it
  returns carries `provider="mock"`; every record `RealVultrProvider`
  returns carries `provider="vultr"`. Nothing downstream can mistake one for
  the other.

```python
from ghostrange_vultr_control import (
    RealVultrProvider, MockVultrProvider,
    CreateWorldRequest, CreateComputeRequest, GhostRangeTags,
)

provider = MockVultrProvider()  # or RealVultrProvider() with VULTR_API_KEY set

tags = GhostRangeTags(range_id="range-123", world_id="world-456")
world = provider.create_world(CreateWorldRequest(region="ewr", tags=tags))
compute = provider.create_compute(CreateComputeRequest(
    world_ref=world.provider_world_id, region="ewr", plan="vc2-1c-1gb",
    tags=tags, os_id=387,  # or snapshot_id=... for the fork path
))
ready = provider.wait_until_ready(compute.provider_compute_id)
provider.destroy_compute(compute.provider_compute_id)
provider.destroy_world(world.provider_world_id, firewall_group_id=world.firewall_group_id)
```

## Status: `REAL_VULTR_E2E = NOT_RUN_NO_CREDENTIALS`

This package's author had no real `VULTR_API_KEY` available while building
it. **No claim is made that `RealVultrProvider` has been exercised against
the live Vultr API.** What has been done instead, honestly:

1. `RealVultrProvider`'s request-construction and response-parsing logic is
   fully unit-tested against a stateful fake of Vultr's HTTP surface
   (`tests/fake_vultr_server.py`) via `httpx.MockTransport` — see
   `tests/test_real_provider_requests.py`. This proves the *shapes* of
   requests this class sends (exact JSON bodies, exact paths/methods, auth
   header) match what Vultr's API documents/its SDK source expects.
2. Every endpoint/field name below was independently verified on
   **2026-09-26** against the current `govultr` v3 Go SDK source
   (https://github.com/vultr/govultr), which mirrors the live Vultr API v2
   request/response schema 1:1 (Vultr's own Terraform provider is generated
   from the same SDK) — not against marketing copy, and not against the
   interactive API reference page (a JS SPA that returns 403/empty to
   headless fetches, so it could not be checked directly).
3. What is **not** verified: that a real POST to `https://api.vultr.com`
   with a real bearer token actually succeeds end-to-end (auth accepted,
   billing account in good standing, region/plan combination valid, etc).
   That requires a real key and real spend, and this package's author had
   neither.

**To run the real E2E once a key exists:**

```bash
export VULTR_API_KEY="<a real Vultr personal access token, API access enabled on the account>"
python - <<'PY'
from ghostrange_vultr_control import RealVultrProvider, CreateWorldRequest, CreateComputeRequest, GhostRangeTags

p = RealVultrProvider()  # reads VULTR_API_KEY from the environment
tags = GhostRangeTags(range_id="smoke-test", ttl_seconds=600)
world = p.create_world(CreateWorldRequest(region="ewr", tags=tags))
print("world:", world.provider_world_id, world.firewall_group_id)
try:
    compute = p.create_compute(CreateComputeRequest(
        world_ref=world.provider_world_id, region="ewr", plan="vc2-1c-1gb",
        tags=tags, os_id=387,  # Debian 12 x64 as of this writing; check `GET /v2/os` for current ids
    ))
    print("compute:", compute.provider_compute_id)
    ready = p.wait_until_ready(compute.provider_compute_id, timeout_s=180)
    print("ready:", ready.status, ready.main_ip)
finally:
    if 'compute' in dir():
        p.destroy_compute(compute.provider_compute_id)
    p.destroy_world(world.provider_world_id, firewall_group_id=world.firewall_group_id)
print("smoke test OK — real instance created and torn down")
PY
```

This is a **manual, gated** smoke test (real spend, real time — instance
create is fast but the account needs a valid payment method and API access
enabled per-account, per Vultr's own docs). It is intentionally not part of
`pytest` — CI never needs, and must never require, a real credential.

**Never**: `VULTR_API_KEY` is read only from the environment
(`os.environ.get("VULTR_API_KEY")`) in `http_client.py`'s
`VultrHTTPClient.__init__`, nowhere else. It is baked once into the
`httpx.Client`'s default headers and never stored as a separate attribute,
never logged (no logging call in this package ever includes the key or the
`Authorization` header), never included in any exception message (every
error path only ever passes a status code + Vultr's own `error` message
string into the typed exceptions in `errors.py`), and never appears in any
test fixture — every test uses an obviously-fake placeholder string.

## Endpoints used (verified 2026-09-26 against `govultr` v3 SDK source)

All requests: `Authorization: Bearer $VULTR_API_KEY`, `Accept: application/json`,
`Content-Type: application/json`, base URL `https://api.vultr.com`.

| Operation | Method + Path | Notes |
|---|---|---|
| Create world (VPC) | `POST /v2/vpcs` | Body: `region`, `description` (encodes GhostRange ownership tags — see below), optionally `v4_subnet`, `v4_subnet_mask`. Response: `{"vpc": {...}}`. |
| Get world | `GET /v2/vpcs/{id}` | Response: `{"vpc": {...}}`. 404 -> `VultrNotFoundError`. |
| List worlds | `GET /v2/vpcs` | Response: `{"vpcs": [...], "meta": {...}}`. |
| Destroy world | `DELETE /v2/vpcs/{id}` | Confirmed gone by polling `GET` until 404 (see below) — a 2xx here does not guarantee the VPC is actually gone. |
| Create firewall group | `POST /v2/firewalls` | Body: `description` only (no native `region`/`tags`). Response: `{"firewall_group": {...}}`. One is created per world by default (`create_firewall_group=True`); this is GhostRange's per-world intra-traffic policy attachment point per ADR-006. |
| Get / delete firewall group | `GET`/`DELETE /v2/firewalls/{id}` | Same confirm-until-gone pattern as VPC delete. |
| Create compute (instance) | `POST /v2/instances` | See field table below. Response: `{"instance": {...}}`. |
| Get compute | `GET /v2/instances/{id}` | Response: `{"instance": {...}}`. |
| List computes | `GET /v2/instances` | Response: `{"instances": [...], "meta": {...}}`. |
| Get compute's attached VPC(s) | `GET /v2/instances/{id}/vpcs` | Used by `get_compute()` to populate `ComputeRecord.world_ref` — the instance object itself does not carry its VPC membership. Response: `{"vpcs": [...], "meta": {...}}`. Best-effort: failure here does not fail `get_compute()`, it just leaves `world_ref=None`. |
| Destroy compute | `DELETE /v2/instances/{id}` | Confirm-until-gone, same pattern. |
| (documented, not called by this package) Bandwidth | `GET /v2/instances/{id}/bandwidth` | Per `docs/research/VULTR.md` §12, Vultr's own docs say this is periodically-refreshed, **not real-time** — out of scope for anything on this package's decision-making path. Not implemented here; if a future coarse cost-accounting job wants it, it belongs in a separate, clearly-optional method, not the core interface. |
| (documented, not called by this package) Create snapshot | `POST /v2/snapshots` (`instance_id`, `description`) | Vultr's own docs: 20–30 minutes, not instant (ADR-006, Decisions.md #12). Golden-snapshot creation is `packages/range-iac`'s concern (the "materialize a base world" compilation mode); `vultr-control`'s job is to accept a pre-existing `snapshot_id` on `CreateComputeRequest` for the fork path, not to create snapshots itself. Add a `create_snapshot()` method here later if a future agent decides vultr-control should own that step too — flagged, not built, to avoid scope creep beyond what M2 wave 1 needs. |

### Instance create field mapping (`POST /v2/instances` body)

| `CreateComputeRequest` field | Vultr API field | Notes |
|---|---|---|
| `region` | `region` | |
| `plan` | `plan` | |
| `os_id` | `os_id` | Fresh build path (ADR-006 "materialize a base world" mode). Mutually exclusive with `snapshot_id` — enforced by a pydantic validator on `CreateComputeRequest`. |
| `snapshot_id` | `snapshot_id` | Fork path (ADR-006 "fork a world" mode) — restore a pre-warmed golden snapshot. |
| `script_id` | `script_id` | Startup script, per ADR-006 reserved for boot-time-critical commands only; prefer `user_data` for role config. |
| `user_data` | `user_data` | **This package base64-encodes it before sending** — Vultr's API expects base64 cloud-config text, matching the Terraform provider's own `base64.StdEncoding.EncodeToString(...)` behavior. |
| `firewall_group_id` | `firewall_group_id` | |
| `world_ref` | `attach_vpc` (a list containing just this one id) | **Correction to ADR-006 / `docs/research/VULTR.md`, which both cite the field as `vpc_ids`.** `vpc_ids` is the *Terraform resource* attribute name (`vultr_instance.vpc_ids`); the Terraform provider translates it internally to `attach_vpc` before calling the raw API (confirmed in `terraform-provider-vultr`'s `resource_vultr_instance.go`: `if vpcIDs, vpcOK := d.GetOk("vpc_ids"); ... req.AttachVPC = append(req.AttachVPC, v.(string))`). Since this package speaks the raw REST API directly (not Terraform), it must and does use `attach_vpc`. `packages/range-iac` is unaffected — it emits Terraform/OpenTofu, where `vpc_ids` is correct. |
| `tags` | `tags` (flat list of opaque strings) | See "Tagging reality" below. |
| `hostname` | `hostname` | |
| `label` | `label` | |
| `enable_ipv6` | `enable_ipv6` | |
| `backups` | `backups` (`"enabled"`/`"disabled"` string, not a bool) | Matches `govultr.InstanceCreateReq.Backups string`. Not used for range assets in M1/M2 per ADR-006 (disposable by design); the field exists on the request type for completeness, defaults to disabled. |

### Also corrected vs. ADR-006 / `docs/research/VULTR.md`: VPC endpoint path

Both docs (written before this package, citing Vultr's docs as of their
research date) refer to **VPC 2.0** and a `/v2/vpc2` endpoint, flagging
"NEEDS VERIFICATION: whether the original (gen-1) VPC is still provisionable
for new accounts." As of 2026-09-26, checked against the current `govultr`
v3 SDK source: **there is no `/v2/vpc2` path in the current SDK.** The VPC
surface has been consolidated into a single `/v2/vpcs` path
(`govultr.VPCService`, `vpcPath = "/v2/vpcs"`), which also now includes NAT
Gateway sub-resources. This package implements against the current,
verified `/v2/vpcs` surface. This does not change any ADOPT/REJECT verdict
in `docs/research/VULTR.md` or any decision in ADR-006 — VPC-based network
isolation per world is still exactly right — it only corrects the literal
path/version label. Flagging prominently here per that doc's own "re-verify
before demo day" instruction; not editing VULTR.md/ADR-006 directly since
this package doesn't own those files (M2_COORDINATION.md ownership table).

### Tagging reality (needed for orphan detection later)

Verified against `govultr` v3: **Vultr instance tags are a flat array of
opaque strings — there is no native key/value tag structure**
(`InstanceCreateReq.Tags []string`). **VPCs and Firewall Groups have no
`tags` field at all** — the only free-text field on either is
`description`. This package's `GhostRangeTags` type encodes ownership
metadata (`range_id`, `world_id`, `created_by`, advisory `ttl_seconds`) as:

- `ghostrange:<key>:<value>` strings in an instance's `tags` list
  (`GhostRangeTags.as_vultr_tag_list()` / `.from_vultr_tag_list()`), and
- a single `ghostrange;key=value;...` string in a VPC/Firewall Group's
  `description` (`GhostRangeTags.as_description()` / `.from_description()`).

`ttl_seconds` is **advisory only** — Vultr has no native expiry/TTL on any
of these resource types. An orphan-reaper job (not built in this package;
this is the metadata substrate for one) would call `list_worlds()` /
`list_computes()` (optionally filtered by `range_id`), parse `tags`, and
compare `created_at + ttl_seconds` to now.

## Reliability behavior

- **Timeouts**: every HTTP call has a bounded timeout (`timeout_s`,
  default 30s) via `httpx.Timeout`. A hung Vultr API call cannot hang
  GhostRange forever.
- **Retry/backoff**: 429 (rate limited) and 5xx responses, and network-level
  failures (`httpx.HTTPError`) and read/connect timeouts, are retried with
  exponential backoff + full jitter (capped at 20s per attempt), up to
  `max_retries` additional attempts (default 5). A `Retry-After` header on a
  429 is honored exactly if present. Any other 4xx (400/401/403/404/409/422)
  is **not** retried — it's a caller bug or a genuinely absent resource;
  retrying an identical malformed request will not fix it.
- **Rate-limit awareness**: Vultr documents a ~30 requests/second limit
  *per source IP* (`docs/research/VULTR.md` §11). Beyond reactive
  429-handling, `VultrHTTPClient` proactively self-throttles to a
  configurable `requests_per_second` (default 15 — half of Vultr's
  documented ceiling, leaving headroom for other processes sharing the same
  egress IP, e.g. other GhostRange workers) via a simple leaky-bucket
  limiter. This is exactly the centralization ADR-006 calls for: "all Vultr
  API access is centralized in `packages/vultr-control` so backoff/retry and
  any future request-queuing lives in exactly one place." If GhostScheduler
  ends up running many worker processes against the same account, a
  cross-process limiter (e.g. a Valkey-backed token bucket) would be the
  next escalation — not built here, since M2 wave 1 has no evidence yet that
  a single process's limiter is insufficient.
- **Error mapping**: every non-2xx response, and every transport failure
  that survives the retry budget, is mapped to one of the typed exceptions
  in `errors.py` (`VultrAuthError`, `VultrNotFoundError`,
  `VultrValidationError`, `VultrConflictError`, `VultrRateLimitedError`,
  `VultrServerError`, `VultrUnavailableError`, `VultrTimeoutError`). No raw
  `httpx` exception or bare status code ever reaches a caller.
- **Deletion confirmation**: `destroy_compute()` / `destroy_world()` never
  trust a 2xx on `DELETE` alone. Each issues the delete, then polls `GET` on
  the same resource until it 404s (`VultrNotFoundError`, treated as success
  internally) or `timeout_s` elapses (raises `VultrTimeoutError`). This
  matters because Vultr's own docs describe resource teardown as
  asynchronous — a 2xx on `DELETE /v2/instances/{id}` means "deletion
  accepted," not "instance is gone."
- **Snapshot latency**: this package does not create snapshots (see table
  above) — it only ever *consumes* a `snapshot_id` on `CreateComputeRequest`.
  The 20–30 minute snapshot-creation latency (Decisions.md #12, ADR-006) is
  therefore not this package's problem to solve, but callers building golden
  snapshots (`packages/range-iac`) must not assume `vultr-control` will make
  that latency disappear — it won't, because it isn't the one calling
  `POST /v2/snapshots`.

## Interface stability (read this before changing `interface.py`)

`packages/range-runtime` and `packages/range-iac` are being built
concurrently against `VultrControlProvider` (per
`docs/milestones/M2_COORDINATION.md`, wave 1). The interface as shipped:

```python
class VultrControlProvider(ABC):
    def create_world(self, req: CreateWorldRequest) -> WorldRecord: ...
    def get_world(self, provider_world_id: str) -> WorldRecord: ...
    def destroy_world(self, provider_world_id: str, *, firewall_group_id=None, timeout_s=120.0, poll_interval_s=3.0) -> None: ...
    def list_worlds(self, *, range_id: str | None = None) -> list[WorldRecord]: ...

    def create_compute(self, req: CreateComputeRequest) -> ComputeRecord: ...
    def get_compute(self, provider_compute_id: str) -> ComputeRecord: ...
    def wait_until_ready(self, provider_compute_id: str, *, timeout_s=300.0, poll_interval_s=5.0) -> ComputeRecord: ...
    def destroy_compute(self, provider_compute_id: str, *, timeout_s=120.0, poll_interval_s=3.0) -> None: ...
    def list_computes(self, *, range_id: str | None = None) -> list[ComputeRecord]: ...
```

This is a **superset** of the task's original conceptual sketch
(`create_world/get_world/create_compute/get_compute/wait_until_ready/destroy_compute/destroy_world`)
— nothing in that original shape was removed or renamed. The additions are:

- `list_worlds()` / `list_computes()` — needed for the orphan-detection use
  case the tagging requirement exists for; there was no way to enumerate
  ownership without them.
- `destroy_world(..., firewall_group_id=...)` — Vultr has no server-side
  link between a VPC and a "paired" firewall group (a firewall group is a
  free-standing resource only ever associated with instances via
  `firewall_group_id` at instance-create time), so if `create_world()` made
  one, the caller must hand it back at `destroy_world()` time to have it
  cleaned up too. Passing `firewall_group_id=None` (the default) skips that
  cleanup and only deletes the VPC — track `WorldRecord.firewall_group_id`
  and pass it through if you created one.

**If this shape must change further**, per `M2_COORDINATION.md`'s
contract-change protocol: propose it, don't land it silently, and flag it
loudly to the other wave-1 agents consuming this package. No such breaking
change was needed while building this package — logged here so a future
change has a clear "this is what existed before" baseline.

`ghostrange_vultr_control.models` types (`CreateWorldRequest`,
`CreateComputeRequest`, `WorldRecord`, `ComputeRecord`, `GhostRangeTags`) are
deliberately **not** the same models as `ghostrange_contracts`
(`WorldV1`, `ComputeWorkerV1`). This package sits one layer below the domain
contracts and speaks Vultr's/the mock's shape, not GhostRange's domain
vocabulary — `range-runtime`/`range-iac` translate between the two layers
(e.g. `WorldV1.id` -> `GhostRangeTags.world_id` as a plain string). This
keeps `vultr-control` usable standalone (a script, a unit test) without
pulling in the whole contracts package, and means a contracts schema change
never forces a change here (or vice versa) unless the *mapping* between them
changes.

## Safety-boundary note (Decisions.md #9)

Per ADR-006's consequences section, this package is "a natural enforcement
point if range-ownership-token checks need to gate API calls," because it is
the only place Vultr API calls originate. No such gating is implemented
yet — no allowlist/ownership-token check exists in this version — this is
flagged for whichever agent wires up Decisions.md #9's safety boundary at
the infrastructure-call layer (see `docs/security/RANGE_NETWORK_BOUNDARY.md`
ownership in `M2_COORDINATION.md`), so they know exactly where to add it:
`RealVultrProvider.create_compute()` / `.create_world()`, before the
`self._http.request(...)` call.

## Development

```bash
cd packages/vultr-control
pip install -e .[dev]
pytest
```

91 tests, all offline (`httpx.MockTransport`, no network access, no real
credentials): `tests/test_models.py` (tagging round-trip + validation),
`tests/test_mock_provider.py` (MockVultrProvider behavior, thorough),
`tests/test_http_client.py` (auth/retry/backoff/rate-limit/error-mapping),
`tests/test_real_provider_requests.py` (RealVultrProvider request-shape
assertions against `tests/fake_vultr_server.py`, a stateful fake of Vultr's
HTTP surface), `tests/test_interface_contract.py` (both implementations
expose identical method signatures and pass the same workflow test).
