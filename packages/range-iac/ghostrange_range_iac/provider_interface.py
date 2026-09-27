"""The Vultr provider interface range-iac compiles against.

Per docs/milestones/M2_COORDINATION.md, `packages/vultr-control` is being built
concurrently by a different agent in this same wave. As of when this module was
written, `packages/vultr-control` is an empty directory (no code to import yet) --
per this package's own task brief: "define the interface you need and document it,
don't block."

So: this module is the CONTRACT range-iac needs from whatever `packages/vultr-control`
ends up exposing, expressed as a `typing.Protocol` (structural typing -- whatever
vultr-control ships does not need to import from here or subclass anything, it just
needs to have methods with these names/signatures, or range-iac needs a thin adapter
written once vultr-control lands). It mirrors the Vultr API v2 fields documented in
docs/research/VULTR.md section 4/5/11 and the ADR-006 field mapping table:

    create-instance fields used: region, plan, os_id | snapshot_id, script_id,
    user_data, vpc_ids, firewall_group_id, hostname, label, tags
    create-vpc2 fields used: region, description, v4_subnet, v4_subnet_mask
    create-firewall-group fields used: description
    create-firewall-rule fields used: ip_type, protocol, port, subnet, subnet_size, notes

Everything in `packages/range-iac/ghostrange_range_iac/compiler.py` produces these
request shapes; nothing in `compiler.py` talks to a real or mocked provider. Only
`apply.py` (and its tests, via `mock_provider.py`) touches this Protocol -- that
split keeps the compiler pure/deterministic/testable with zero network or process
dependencies, per the M2 task's testing requirement.

Reconciliation note for Agent 02 (packages/vultr-control): if your real client's
method names/signatures differ from this Protocol, either (a) rename to match --
cheapest for the project -- or (b) tell me and I'll add a thin adapter in
`apply.py`. Either way this file is the single source of truth for what range-iac
needs, so a mismatch is a five-minute fix, not a redesign.
"""

from __future__ import annotations

from typing import Literal, Optional, Protocol

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request shapes (what range-iac's compiler produces)
# ---------------------------------------------------------------------------


class VPCCreateRequest(BaseModel):
    """Maps 1:1 to POST /v2/vpc2 (see docs/research/VULTR.md section 5)."""

    ref: str = Field(..., description="Local, compile-time-only reference id, e.g. 'range-vpc'")
    region: str
    description: str
    v4_subnet: str
    v4_subnet_mask: int


class FirewallGroupCreateRequest(BaseModel):
    ref: str = Field(..., description="Local reference id, e.g. 'range-fw'")
    description: str


class FirewallRuleCreateRequest(BaseModel):
    """Maps to a `vultr_firewall_rule` entry attached to a firewall_group_id.

    ``subnet``/``subnet_size`` follow Vultr's CIDR-split representation
    (e.g. subnet="0.0.0.0", subnet_size=0 for "anywhere").
    """

    firewall_group_ref: str = Field(..., description="Must match a FirewallGroupCreateRequest.ref")
    ip_type: Literal["v4", "v6"] = "v4"
    protocol: Literal["tcp", "udp", "icmp"] = "tcp"
    port: str = Field(..., description="Single port or range as a string, e.g. '443' or '8000:8010'")
    subnet: str
    subnet_size: int
    notes: str = ""


class InstanceCreateRequest(BaseModel):
    """Maps 1:1 to POST /v2/instances (see docs/research/VULTR.md section 4).

    ``vpc_refs``/``firewall_group_ref`` are LOCAL references at compile time (the
    real Vultr ids don't exist until the VPC/firewall group have actually been
    created) -- ``apply.py`` resolves these to real ``vpc_ids``/``firewall_group_id``
    values before issuing the real create-instance call. ``user_data`` is the raw
    cloud-init YAML text; base64-encoding it is a wire-format concern the real
    Vultr client (packages/vultr-control) owns, not range-iac.
    """

    physical_group_id: str = Field(
        ..., description="PhysicalGroupV1.id this request was compiled from (for traceability)"
    )
    hostname: str
    label: str
    region: str
    plan: str
    os_id: Optional[int] = None
    snapshot_id: Optional[str] = None
    script_id: Optional[str] = None
    user_data: Optional[str] = None
    vpc_refs: list[str] = Field(default_factory=list)
    firewall_group_ref: Optional[str] = None
    disable_public_ipv4: bool = False
    tags: list[str] = Field(default_factory=list)


class CompiledRangeInfra(BaseModel):
    """The full, deterministic output of `compiler.compile_range(...)` for one range.

    Pure data -- no provider calls have happened when this object exists. Two of
    these (mode="base" vs mode="fork") differ only in how `instances[i].os_id` vs
    `.snapshot_id` got populated; see compiler.py.
    """

    range_id: str
    range_name: str
    mode: Literal["base", "fork"]
    vpc: VPCCreateRequest
    firewall_group: FirewallGroupCreateRequest
    firewall_rules: list[FirewallRuleCreateRequest]
    instances: list[InstanceCreateRequest]


# ---------------------------------------------------------------------------
# Response shapes (what a real or mocked provider hands back)
# ---------------------------------------------------------------------------


class ProvisionedVPC(BaseModel):
    vultr_vpc_id: str
    region: str


class ProvisionedFirewallGroup(BaseModel):
    vultr_firewall_group_id: str


class ProvisionedInstance(BaseModel):
    vultr_instance_id: str
    hostname: str
    main_ip: Optional[str] = None
    status: str = "pending"


class AppliedRangeInfra(BaseModel):
    """What `apply.apply_compiled_infra(...)` returns: real Vultr ids for everything
    `CompiledRangeInfra` described, keyed the same way so callers can correlate.
    """

    range_id: str
    vpc: ProvisionedVPC
    firewall_group: ProvisionedFirewallGroup
    instances: list[ProvisionedInstance]


# ---------------------------------------------------------------------------
# The provider Protocol itself
# ---------------------------------------------------------------------------


class VultrProviderProtocol(Protocol):
    """Structural interface range-iac needs from packages/vultr-control.

    Every method is a direct wrapper around one Vultr API v2 call (see
    docs/research/VULTR.md section 11 for the endpoint list). Retry/backoff on
    HTTP 429 and the ~30 req/s rate limit are the implementation's problem, not the
    caller's -- range-iac assumes calls either succeed or raise, and does not retry.
    """

    def create_vpc2(self, req: VPCCreateRequest) -> ProvisionedVPC: ...

    def create_firewall_group(self, req: FirewallGroupCreateRequest) -> ProvisionedFirewallGroup: ...

    def create_firewall_rule(self, firewall_group_id: str, req: FirewallRuleCreateRequest) -> None: ...

    def create_instance(self, req: InstanceCreateRequest, vpc_ids: list[str], firewall_group_id: Optional[str]) -> ProvisionedInstance: ...

    def get_instance(self, instance_id: str) -> ProvisionedInstance: ...

    def terminate_instance(self, instance_id: str) -> None: ...

    def list_instances(self) -> list[ProvisionedInstance]: ...


__all__ = [
    "VPCCreateRequest",
    "FirewallGroupCreateRequest",
    "FirewallRuleCreateRequest",
    "InstanceCreateRequest",
    "CompiledRangeInfra",
    "ProvisionedVPC",
    "ProvisionedFirewallGroup",
    "ProvisionedInstance",
    "AppliedRangeInfra",
    "VultrProviderProtocol",
]
