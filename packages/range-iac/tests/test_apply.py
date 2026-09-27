"""apply.py wiring tests against MockVultrProvider (no live Vultr credentials --
see mock_provider.py's docstring and docs/adr/ADR-M2-RANGE-PROVISIONING.md's
REPRODUCIBILITY section for why live-credential testing is explicitly out of scope
for this deliverable)."""

from __future__ import annotations

from pathlib import Path

from ghostrange_range_iac.apply import apply_compiled_infra
from ghostrange_range_iac.compiler import compile_range
from ghostrange_range_iac.loader import load_range
from ghostrange_range_iac.mock_provider import MockVultrProvider


def test_apply_creates_vpc_then_firewall_then_instances_in_order(range_dir: Path):
    spec, topology, compose_by_group, support_files_by_group = load_range(range_dir)
    result = compile_range(
        spec,
        topology,
        mode="base",
        compose_by_group=compose_by_group,
        support_files_by_group=support_files_by_group,
    )

    provider = MockVultrProvider()
    applied = apply_compiled_infra(result.infra, provider)

    assert len(provider.created_vpcs) == 1
    assert len(provider.created_firewall_groups) == 1
    assert len(provider.created_firewall_rules) == 1  # the INTERNET -> gw01 rule
    assert len(provider.created_instances) == 1

    assert applied.range_id == str(spec.id)
    assert applied.vpc.vultr_vpc_id.startswith("vpc-")
    assert applied.firewall_group.vultr_firewall_group_id.startswith("fwg-")
    assert len(applied.instances) == 1
    assert applied.instances[0].hostname == "ghostrange-auth-lab-v1-vm-1"
    # Public IP present because this instance hosts the gateway (INTERNET edge target).
    assert applied.instances[0].main_ip is not None


def test_apply_rejects_a_ref_that_was_never_compiled(range_dir: Path):
    spec, topology, compose_by_group, support_files_by_group = load_range(range_dir)
    result = compile_range(
        spec,
        topology,
        mode="base",
        compose_by_group=compose_by_group,
        support_files_by_group=support_files_by_group,
    )
    result.infra.instances[0].vpc_refs = ["some-other-vpc-ref"]

    provider = MockVultrProvider()
    try:
        apply_compiled_infra(result.infra, provider)
        assert False, "expected a ValueError for the unknown vpc ref"
    except ValueError:
        pass
