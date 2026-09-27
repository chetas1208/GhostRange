from __future__ import annotations

from pathlib import Path

import yaml
from ghostrange_contracts.range import RangeSpecV1
from ghostrange_range_iac.models import INTERNET, RangeTopologyPlanV1


def _load_spec(range_dir: Path) -> RangeSpecV1:
    raw = yaml.safe_load((range_dir / "rangespec.yaml").read_text(encoding="utf-8"))
    return RangeSpecV1.model_validate(raw)


def _load_topology(range_dir: Path) -> RangeTopologyPlanV1:
    raw = yaml.safe_load((range_dir / "topology.yaml").read_text(encoding="utf-8"))
    return RangeTopologyPlanV1.model_validate(raw)


def test_topology_yaml_validates(range_dir: Path):
    topology = _load_topology(range_dir)
    assert topology.range_name == "ghostrange-auth-lab-v1"
    assert len(topology.physical_groups) == 1
    assert topology.physical_groups[0].id == "vm-1"


def test_topology_matches_rangespec_ids(range_dir: Path):
    spec = _load_spec(range_dir)
    topology = _load_topology(range_dir)

    assert topology.range_spec_id == spec.id

    spec_asset_ids = {a.id for a in spec.assets}
    placed_ids = {aid for group in topology.physical_groups for aid in group.asset_ids}
    assert placed_ids == spec_asset_ids, "every RangeSpec asset must be placed exactly once"


def test_topology_edges_reference_real_hostnames(range_dir: Path):
    spec = _load_spec(range_dir)
    topology = _load_topology(range_dir)

    hostnames = {a.hostname for a in spec.assets}
    for edge in topology.edges:
        assert edge.to_asset in hostnames
        assert edge.from_asset == INTERNET or edge.from_asset in hostnames


def test_internet_edge_targets_the_gateway(range_dir: Path):
    topology = _load_topology(range_dir)
    internet_edges = [e for e in topology.edges if e.from_asset == INTERNET]
    assert len(internet_edges) == 1
    assert internet_edges[0].to_asset == "gw01"
