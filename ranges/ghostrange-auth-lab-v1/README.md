# ghostrange-auth-lab-v1

The canonical M2 provisioning range. Owned by Agent 03 (Infrastructure / Range
Provisioning) for the LOGICAL spec + PHYSICAL topology + provisioning artifacts in
this directory; the actual auth-lab **scenario** (real application logic, injected
vulnerabilities/CVEs) is owned by the wave-2 "controlled scenario" agent (see
`docs/milestones/M2_COORDINATION.md`, item 06) and will replace the placeholder
services below without needing to touch `rangespec.yaml`, `topology.yaml`, or
`packages/range-iac`'s compiler.

## What's here

| File | Layer | Owned by |
|---|---|---|
| `rangespec.yaml` | LOGICAL — a real `RangeSpecV1` | this deliverable (frozen contract, wave-1) |
| `topology.yaml` | PHYSICAL placement + reachability edges — `RangeTopologyPlanV1` (`packages/range-iac`) | this deliverable |
| `docker/vm-1/docker-compose.yml` | The real compose file booted on the one physical VM `vm-1` consolidates all 4 logical assets onto for M2 | this deliverable (placeholder services) |
| `docker/vm-1/files/**` | Support config (nginx.conf, init.sql) + minimal stdlib-only app stubs for api/auth | this deliverable (placeholder) |

## Logical topology

```
INTERNET / TEST ORIGIN --80/tcp--> gw01 (gateway, LOAD_BALANCER)
                                       |
                                  8080/tcp
                                       v
                                   api01 (api, SERVER)
                                       |
                                  8090/tcp
                                       v
                                  auth01 (auth, SERVER)
                                       |
                                  5432/tcp
                                       v
                                   db01 (data store, DATABASE)
```

Declared in `rangespec.yaml` as 4 `AssetSpecV1` entries on one `NetworkSpecV1`
("auth-lab-core", `10.60.0.0/24`); reachability edges declared in `topology.yaml`,
not in the RangeSpec (RangeSpecV1 has no edge/reachability field — see the ADR).

## Physical layout (M2)

All four logical assets are consolidated onto **one** physical Vultr Compute
instance, `vm-1` (region `ewr`, plan `vc2-2c-4gb`), via docker-compose. This is
`topology.yaml`'s call, not `rangespec.yaml`'s — a future topology.yaml for this
same range could spread the four assets across four physical VMs (e.g. once
GhostScheduler wants per-tier resource isolation or per-tier snapshot/fork
granularity) with **zero changes to `rangespec.yaml`**. `packages/range-iac`'s
compiler test suite (`packages/range-iac/tests/test_compiler.py`) exercises both
layouts: the real single-VM one here, and a synthetic two-VM fixture that proves
the compiler correctly emits a real Vultr firewall rule for an edge that crosses
physical hosts, while a same-host edge (all of this range's edges, today) emits
none.

Because everything is on one VM, only the `INTERNET -> gw01` edge crosses the real
Vultr network fabric and gets a compiled firewall rule (allow tcp/80 from anywhere).
The other three edges are same-host, handled entirely by docker-compose's own
`authlab-net` bridge network — see `docs/adr/ADR-M2-RANGE-PROVISIONING.md` for why
that distinction matters.

## Running it locally (no Vultr, no cloud-init — just docker compose)

```bash
cd ranges/ghostrange-auth-lab-v1/docker/vm-1
mkdir -p /tmp/ghostrange-authlab && cp -r files/* /tmp/ghostrange-authlab/  # simulate /opt/ghostrange
# then edit the compose file's bind-mount sources to /tmp/ghostrange-authlab/... or
# just `docker compose -f docker-compose.yml up -d` from a copy where files/ has been
# relocated to match the compose file's /opt/ghostrange/* paths (that relocation is
# exactly what cloud-init does on a real instance -- see packages/range-iac/ghostrange_range_iac/loader.py
# and cloud_init.py).
curl localhost/health        # -> gateway ok
curl -X POST localhost/api/login -d '{"username":"demo","password":"ghostrange-lab-only"}' \
     -H 'Content-Type: application/json'   # -> proxied through api -> auth -> checks vs demo creds
```

(`demo` / `ghostrange-lab-only` is an intentionally fake, lab-only credential —
never a real secret. See `docker/vm-1/files/auth/app.py`.)

## Compiling it to real Vultr requests

```python
from ghostrange_range_iac import load_range, compile_range
spec, topology, compose_by_group, support_files_by_group = load_range("ranges/ghostrange-auth-lab-v1")
result = compile_range(spec, topology, mode="base", compose_by_group=compose_by_group,
                        support_files_by_group=support_files_by_group)
```

See `packages/range-iac/README.md` for the full compile -> apply flow, and
`docs/adr/ADR-M2-RANGE-PROVISIONING.md` for base-vs-fork mode, teardown behavior, and
why this range is provisioned via direct Vultr API calls (through
`packages/vultr-control`'s eventual client) rather than generated OpenTofu HCL.
