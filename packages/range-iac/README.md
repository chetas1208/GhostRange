# ghostrange-range-iac

Compiles a **LOGICAL** `RangeSpecV1` (packages/contracts) plus a **PHYSICAL**
`RangeTopologyPlanV1` (this package's own `models.py`) into the exact set of Vultr
provisioning requests (VPC 2.0, Firewall Group + rules, one or more Compute instance
creates) needed to stand a range up, plus the real cloud-init `user_data` content
each instance boots with.

Read `docs/adr/ADR-M2-RANGE-PROVISIONING.md` first for the design rationale. Short
version:

- **`RangeSpecV1` never says which physical VM anything runs on.** That mapping
  lives in a `RangeTopologyPlanV1` (`ghostrange_range_iac/models.py`), checked in
  next to the spec as `<range dir>/topology.yaml`. This is deliberate: GhostScheduler
  will eventually move logical assets between physical hosts, and it must be able to
  do that by editing only the topology plan.
- **The compiler (`compiler.py`) is pure** — RangeSpec + topology + docker-compose
  text in, a `CompiledRangeInfra` (request objects with *local* refs like
  `"range-vpc"`, not real Vultr ids) out. No network calls, fully deterministic,
  fully unit-testable.
- **`apply.py` is the only module that calls a provider.** It resolves local refs to
  real ids in the correct order (VPC → firewall group → firewall rules → instances)
  against anything implementing `provider_interface.VultrProviderProtocol`.
- **`packages/vultr-control` is being built concurrently by a different M2 agent.**
  As of writing it's an empty directory, so `provider_interface.py` defines the
  Protocol range-iac needs and documents how to reconcile once real code lands (see
  that file's docstring). Tests run against `mock_provider.MockVultrProvider`.

## Module map

| Module | What it does |
|---|---|
| `models.py` | `RangeTopologyPlanV1`, `PhysicalGroupV1`, `ReachabilityEdgeV1` — the PHYSICAL model family, not part of `ghostrange_contracts` |
| `loader.py` | Reads `<range dir>/{rangespec.yaml,topology.yaml,docker/<group>/...}` into Python objects |
| `compiler.py` | `compile_range(spec, topology, ...) -> CompileResult` — the pure compiler |
| `cloud_init.py` | Renders real `#cloud-config` YAML (base-mode installs docker; fork-mode assumes a golden snapshot already has it) |
| `provider_interface.py` | Request/response shapes + the `VultrProviderProtocol` this package needs from vultr-control |
| `mock_provider.py` | Deterministic fake provider for tests (no live credentials anywhere in this repo) |
| `apply.py` | Resolves a `CompiledRangeInfra`'s local refs to real ids and calls the provider |

## Directory convention for a range

```
ranges/<name>/
  rangespec.yaml              RangeSpecV1 (LOGICAL)
  topology.yaml                RangeTopologyPlanV1 (PHYSICAL placement + edges)
  docker/<group_id>/docker-compose.yml
  docker/<group_id>/files/**    -> written on that instance at /opt/ghostrange/**
```

`ranges/ghostrange-auth-lab-v1/` is the canonical, working example — one physical
group (`vm-1`) hosting all four logical assets (gateway, api, auth, data store).

## Usage

```python
from ghostrange_range_iac import load_range, compile_range
from ghostrange_range_iac.apply import apply_compiled_infra
from ghostrange_range_iac.mock_provider import MockVultrProvider  # or a real provider

spec, topology, compose_by_group, support_files_by_group = load_range("ranges/ghostrange-auth-lab-v1")
result = compile_range(spec, topology, mode="base", compose_by_group=compose_by_group,
                        support_files_by_group=support_files_by_group)

applied = apply_compiled_infra(result.infra, MockVultrProvider())
```

To fork a world from an existing golden snapshot instead of materializing from a
bare OS, pass `mode="fork"` and `snapshot_map={"vm-1": "<a real Vultr snapshot id>"}`
— never create the snapshot itself as part of this call (see the ADR: snapshot
creation is a documented 20–30 minute Vultr operation and must never be on a fork's
critical path).

## Testing

`pytest packages/range-iac/tests` — all tests are deterministic and require no live
Vultr credentials: the compiler is pure, and `apply.py` is only exercised against
`MockVultrProvider`. There is no live-credential smoke test in this deliverable;
adding one (gated behind an env var, per `docs/research/VULTR.md`'s own testing
guidance) is future work once `packages/vultr-control` ships real credential
handling.

## Install

```bash
pip install -e "packages/range-iac[dev]"
```
