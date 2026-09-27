from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from ghostrange_contracts.enums import AssetRole
from ghostrange_contracts.range import AssetSpecV1, NetworkSpecV1, RangeSpecV1
from ghostrange_range_iac.compiler import TopologyMismatchError, compile_range
from ghostrange_range_iac.loader import load_range
from ghostrange_range_iac.models import PhysicalGroupV1, RangeTopologyPlanV1, ReachabilityEdgeV1


def _flat_runcmd(user_data: str) -> list[str]:
    parsed = yaml.safe_load(user_data[len("#cloud-config\n") :])
    return [" ".join(c) if isinstance(c, list) else c for c in parsed["runcmd"]]


# ---------------------------------------------------------------------------
# The real canonical range: ghostrange-auth-lab-v1, single-VM M2 layout
# ---------------------------------------------------------------------------


def test_compile_canonical_range_base_mode(range_dir: Path):
    spec, topology, compose_by_group, support_files_by_group = load_range(range_dir)

    result = compile_range(
        spec,
        topology,
        mode="base",
        compose_by_group=compose_by_group,
        support_files_by_group=support_files_by_group,
    )
    infra = result.infra

    assert infra.mode == "base"
    assert infra.range_name == "ghostrange-auth-lab-v1"

    # Exactly one physical instance for M2's single-VM consolidation of 4 logical assets.
    assert len(infra.instances) == 1
    inst = infra.instances[0]
    assert inst.os_id == 1743
    assert inst.snapshot_id is None
    assert inst.disable_public_ipv4 is False
    assert inst.vpc_refs == ["range-vpc"]
    assert inst.firewall_group_ref == "range-fw"
    for tag in ("asset:gw01", "asset:api01", "asset:auth01", "asset:db01"):
        assert tag in inst.tags

    # Only the INTERNET -> gw01 edge crosses the Vultr network fabric; the other 3
    # edges are same-host (docker-compose's own network) and need no firewall rule.
    assert len(infra.firewall_rules) == 1
    rule = infra.firewall_rules[0]
    assert rule.port == "80"
    assert rule.subnet == "0.0.0.0" and rule.subnet_size == 0

    treatments = {(r.from_asset, r.to_asset): r.treatment for r in result.edge_report}
    assert treatments[("INTERNET", "gw01")] == "internet_ingress_firewall_rule"
    assert treatments[("gw01", "api01")] == "same_host_no_rule_needed"
    assert treatments[("api01", "auth01")] == "same_host_no_rule_needed"
    assert treatments[("auth01", "db01")] == "same_host_no_rule_needed"

    # cloud-init: base mode installs docker and boots the real compose file.
    assert inst.user_data is not None
    assert inst.user_data.startswith("#cloud-config")
    runcmd = _flat_runcmd(inst.user_data)
    assert any("get-docker.sh" in c for c in runcmd)
    assert any("docker compose -f /opt/ghostrange/docker-compose.yml up -d" in c for c in runcmd)
    assert "gateway" in inst.user_data and "data-store" in inst.user_data  # compose content embedded


def test_compile_canonical_range_fork_mode_skips_docker_install(range_dir: Path):
    spec, topology, compose_by_group, support_files_by_group = load_range(range_dir)

    result = compile_range(
        spec,
        topology,
        mode="fork",
        compose_by_group=compose_by_group,
        support_files_by_group=support_files_by_group,
        snapshot_map={"vm-1": "snap-golden-0001"},
    )
    inst = result.infra.instances[0]

    assert inst.os_id is None
    assert inst.snapshot_id == "snap-golden-0001"
    runcmd = _flat_runcmd(inst.user_data)
    assert not any("get-docker.sh" in c for c in runcmd)  # fork restores a snapshot that already has docker
    assert any("docker compose -f /opt/ghostrange/docker-compose.yml up -d" in c for c in runcmd)


def test_fork_mode_requires_snapshot_map(range_dir: Path):
    spec, topology, compose_by_group, support_files_by_group = load_range(range_dir)
    with pytest.raises(ValueError):
        compile_range(
            spec,
            topology,
            mode="fork",
            compose_by_group=compose_by_group,
            support_files_by_group=support_files_by_group,
        )


# ---------------------------------------------------------------------------
# Synthetic 2-VM fixture: exercises cross-host firewall-rule compilation, which
# ghostrange-auth-lab-v1's single-VM M2 layout never triggers on its own. This is
# exactly the "GhostScheduler moves a logical asset to a different physical host"
# case ADR-M2-RANGE-PROVISIONING.md and models.py's docstring call out.
# ---------------------------------------------------------------------------


def _two_tier_spec_and_topology() -> tuple[RangeSpecV1, RangeTopologyPlanV1]:
    net = NetworkSpecV1(name="net", cidr="10.70.0.0/24")
    front = AssetSpecV1(hostname="front01", network_id=net.id, os_family="linux", role=AssetRole.SERVER, image="x")
    back = AssetSpecV1(hostname="back01", network_id=net.id, os_family="linux", role=AssetRole.DATABASE, image="y")
    spec = RangeSpecV1(name="two-tier-synthetic", owner="test@example.com", networks=[net], assets=[front, back])

    topology = RangeTopologyPlanV1(
        range_spec_id=spec.id,
        range_name="two-tier-synthetic",
        physical_groups=[
            PhysicalGroupV1(id="vm-front", asset_ids=[front.id], region="ewr", plan="vc2-1c-1gb", os_id=1743, needs_public_ip=True),
            PhysicalGroupV1(id="vm-back", asset_ids=[back.id], region="ewr", plan="vc2-1c-1gb", os_id=1743, needs_public_ip=False),
        ],
        edges=[
            ReachabilityEdgeV1(from_asset="INTERNET", to_asset="front01", port=443, protocol="tcp"),
            ReachabilityEdgeV1(from_asset="front01", to_asset="back01", port=5432, protocol="tcp"),
        ],
    )
    return spec, topology


def test_cross_host_edge_compiles_to_a_firewall_rule():
    spec, topology = _two_tier_spec_and_topology()
    result = compile_range(
        spec,
        topology,
        mode="base",
        compose_by_group={"vm-front": "services: {}\n", "vm-back": "services: {}\n"},
    )

    assert len(result.infra.instances) == 2
    treatments = {(r.from_asset, r.to_asset): r.treatment for r in result.edge_report}
    assert treatments[("INTERNET", "front01")] == "internet_ingress_firewall_rule"
    assert treatments[("front01", "back01")] == "cross_host_firewall_rule"

    # Two real edges that both leave a physical group -> two real firewall rules.
    assert len(result.infra.firewall_rules) == 2

    front_inst = next(i for i in result.infra.instances if i.physical_group_id == "vm-front")
    back_inst = next(i for i in result.infra.instances if i.physical_group_id == "vm-back")
    assert front_inst.disable_public_ipv4 is False
    assert back_inst.disable_public_ipv4 is True


def test_needs_public_ip_mismatch_is_rejected():
    spec, topology = _two_tier_spec_and_topology()
    # Corrupt the declared flag so it disagrees with what the INTERNET edge implies.
    topology.physical_groups[0].needs_public_ip = False

    with pytest.raises(TopologyMismatchError):
        compile_range(
            spec,
            topology,
            mode="base",
            compose_by_group={"vm-front": "services: {}\n", "vm-back": "services: {}\n"},
        )


def test_unplaced_asset_is_rejected():
    spec, topology = _two_tier_spec_and_topology()
    # Drop the vm-back group entirely -> back01 is never placed anywhere.
    topology.physical_groups = [topology.physical_groups[0]]

    with pytest.raises(TopologyMismatchError):
        compile_range(spec, topology, mode="base", compose_by_group={"vm-front": "x", "vm-back": "y"})


def test_duplicate_placement_is_rejected():
    spec, topology = _two_tier_spec_and_topology()
    # Place the front asset in both groups.
    topology.physical_groups[1].asset_ids = list(topology.physical_groups[0].asset_ids)

    with pytest.raises(TopologyMismatchError):
        compile_range(spec, topology, mode="base", compose_by_group={"vm-front": "x", "vm-back": "y"})


def test_mismatched_range_spec_id_is_rejected():
    spec, topology = _two_tier_spec_and_topology()
    topology.range_spec_id = spec.id.__class__(int=0)  # a different, well-formed UUID

    with pytest.raises(TopologyMismatchError):
        compile_range(spec, topology, mode="base", compose_by_group={"vm-front": "x", "vm-back": "y"})
