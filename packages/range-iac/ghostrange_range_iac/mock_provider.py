"""Deterministic mock implementing VultrProviderProtocol, for tests only.

No live Vultr credentials exist anywhere in this repo yet (see ADR-006's
Consequences section). This mock is what `apply.py`'s tests run against; a real
implementation lives (or will live) in `packages/vultr-control`, built by a different
agent in this same M2 wave -- see provider_interface.py's module docstring for the
reconciliation note.
"""

from __future__ import annotations

from .provider_interface import (
    FirewallGroupCreateRequest,
    FirewallRuleCreateRequest,
    InstanceCreateRequest,
    ProvisionedFirewallGroup,
    ProvisionedInstance,
    ProvisionedVPC,
    VPCCreateRequest,
)


class MockVultrProvider:
    """Records every call it receives and hands back deterministic fake ids.

    Deliberately simple: no simulated latency, no simulated 429s (that belongs in a
    dedicated retry/backoff test for whatever client packages/vultr-control ships,
    not here) -- this mock exists purely to prove `apply.py`'s wiring (VPC -> firewall
    group -> firewall rules -> instances, in that order, with refs correctly resolved
    to real ids) is correct.
    """

    def __init__(self) -> None:
        self.created_vpcs: list[VPCCreateRequest] = []
        self.created_firewall_groups: list[FirewallGroupCreateRequest] = []
        self.created_firewall_rules: list[tuple[str, FirewallRuleCreateRequest]] = []
        self.created_instances: list[InstanceCreateRequest] = []
        self.terminated_instance_ids: list[str] = []
        self._instances: dict[str, ProvisionedInstance] = {}
        self._counter = 0

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter:04d}"

    def create_vpc2(self, req: VPCCreateRequest) -> ProvisionedVPC:
        self.created_vpcs.append(req)
        return ProvisionedVPC(vultr_vpc_id=self._next_id("vpc"), region=req.region)

    def create_firewall_group(self, req: FirewallGroupCreateRequest) -> ProvisionedFirewallGroup:
        self.created_firewall_groups.append(req)
        return ProvisionedFirewallGroup(vultr_firewall_group_id=self._next_id("fwg"))

    def create_firewall_rule(self, firewall_group_id: str, req: FirewallRuleCreateRequest) -> None:
        self.created_firewall_rules.append((firewall_group_id, req))

    def create_instance(
        self,
        req: InstanceCreateRequest,
        vpc_ids: list[str],
        firewall_group_id: str | None,
    ) -> ProvisionedInstance:
        self.created_instances.append(req)
        instance_id = self._next_id("inst")
        provisioned = ProvisionedInstance(
            vultr_instance_id=instance_id,
            hostname=req.hostname,
            main_ip=f"203.0.113.{len(self._instances) + 1}" if not req.disable_public_ipv4 else None,
            status="pending",
        )
        self._instances[instance_id] = provisioned
        return provisioned

    def get_instance(self, instance_id: str) -> ProvisionedInstance:
        return self._instances[instance_id]

    def terminate_instance(self, instance_id: str) -> None:
        self.terminated_instance_ids.append(instance_id)
        self._instances.pop(instance_id, None)

    def list_instances(self) -> list[ProvisionedInstance]:
        return list(self._instances.values())


__all__ = ["MockVultrProvider"]
