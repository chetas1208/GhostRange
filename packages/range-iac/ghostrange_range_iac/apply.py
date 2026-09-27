"""Executes a `CompiledRangeInfra` against a real (or mocked) `VultrProviderProtocol`.

This is the ONLY module in range-iac that calls provider methods. `compiler.py`'s
output is pure data with local references (`vpc_refs=["range-vpc"]`,
`firewall_group_ref="range-fw"`) instead of real Vultr ids, because those ids don't
exist until the VPC and firewall group have actually been created -- this module does
that two-phase resolution: create the VPC + firewall group (+ its rules) first, then
substitute the real ids into every instance create call.

No live Vultr credentials exist in this repo (see ADR-006 Consequences). Tests for
this module run exclusively against `mock_provider.MockVultrProvider`. A live-credential
smoke test is intentionally not included here -- gate any such test behind an env var
per docs/research/VULTR.md's own testing guidance, once `packages/vultr-control` ships
real credentials handling.
"""

from __future__ import annotations

from .provider_interface import (
    AppliedRangeInfra,
    CompiledRangeInfra,
    ProvisionedInstance,
    VultrProviderProtocol,
)


def apply_compiled_infra(
    compiled: CompiledRangeInfra, provider: VultrProviderProtocol
) -> AppliedRangeInfra:
    provisioned_vpc = provider.create_vpc2(compiled.vpc)
    provisioned_fw = provider.create_firewall_group(compiled.firewall_group)

    for rule in compiled.firewall_rules:
        if rule.firewall_group_ref != compiled.firewall_group.ref:
            raise ValueError(
                f"firewall rule references '{rule.firewall_group_ref}' but compiled "
                f"firewall group ref is '{compiled.firewall_group.ref}'"
            )
        provider.create_firewall_rule(provisioned_fw.vultr_firewall_group_id, rule)

    provisioned_instances: list[ProvisionedInstance] = []
    for inst_req in compiled.instances:
        for ref in inst_req.vpc_refs:
            if ref != compiled.vpc.ref:
                raise ValueError(f"instance references unknown vpc ref '{ref}'")
        vpc_ids = [provisioned_vpc.vultr_vpc_id for _ in inst_req.vpc_refs]

        firewall_group_id = None
        if inst_req.firewall_group_ref is not None:
            if inst_req.firewall_group_ref != compiled.firewall_group.ref:
                raise ValueError(
                    f"instance references unknown firewall group ref "
                    f"'{inst_req.firewall_group_ref}'"
                )
            firewall_group_id = provisioned_fw.vultr_firewall_group_id

        provisioned = provider.create_instance(inst_req, vpc_ids, firewall_group_id)
        provisioned_instances.append(provisioned)

    return AppliedRangeInfra(
        range_id=compiled.range_id,
        vpc=provisioned_vpc,
        firewall_group=provisioned_fw,
        instances=provisioned_instances,
    )


__all__ = ["apply_compiled_infra"]
