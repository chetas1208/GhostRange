"""Proves ranges/ghostrange-auth-lab-v1/rangespec.yaml is a real, valid RangeSpecV1.

This is the exact proof the M2 task brief asked for:
``RangeSpecV1.model_validate(yaml.safe_load(open(...)))`` must succeed against the
real Pydantic model in packages/contracts/ghostrange_contracts/range.py -- not a
hand-rolled schema that merely looks similar.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from ghostrange_contracts.enums import AssetRole, SecurityCriticality
from ghostrange_contracts.range import RangeSpecV1


def test_rangespec_yaml_validates_against_real_model(range_dir: Path):
    raw = yaml.safe_load((range_dir / "rangespec.yaml").read_text(encoding="utf-8"))
    spec = RangeSpecV1.model_validate(raw)

    assert spec.name == "ghostrange-auth-lab-v1"
    assert spec.schema_version == "1"
    assert spec.owner == "chetasparekh2003@gmail.com"


def test_rangespec_has_expected_logical_topology(range_dir: Path):
    raw = yaml.safe_load((range_dir / "rangespec.yaml").read_text(encoding="utf-8"))
    spec = RangeSpecV1.model_validate(raw)

    assert len(spec.networks) == 1
    assert len(spec.assets) == 4

    by_hostname = {a.hostname: a for a in spec.assets}
    assert set(by_hostname) == {"gw01", "api01", "auth01", "db01"}

    # Every asset must reference the one declared network -- a dangling network_id
    # would validate against RangeSpecV1's shape (network_id is just a UUID field)
    # but be a real inconsistency the compiler must not silently tolerate.
    network_ids = {n.id for n in spec.networks}
    for asset in spec.assets:
        assert asset.network_id in network_ids

    assert by_hostname["gw01"].role == AssetRole.LOAD_BALANCER
    assert by_hostname["api01"].role == AssetRole.SERVER
    assert by_hostname["auth01"].role == AssetRole.SERVER
    assert by_hostname["db01"].role == AssetRole.DATABASE

    assert by_hostname["auth01"].criticality == SecurityCriticality.HIGH
    assert by_hostname["db01"].criticality == SecurityCriticality.HIGH


def test_rangespec_round_trips_through_json(range_dir: Path):
    """A RangeSpecV1 that survives model_dump -> model_validate is the real proof it
    behaves like every other contract model (see packages/contracts/README.md's
    versioning convention), not just that YAML happens to parse."""
    raw = yaml.safe_load((range_dir / "rangespec.yaml").read_text(encoding="utf-8"))
    spec = RangeSpecV1.model_validate(raw)

    dumped = spec.model_dump(mode="json")
    reloaded = RangeSpecV1.model_validate(dumped)
    assert reloaded == spec
