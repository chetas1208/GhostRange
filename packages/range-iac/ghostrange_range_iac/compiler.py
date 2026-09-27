"""RangeSpecV1 + RangeTopologyPlanV1 -> CompiledRangeInfra.

This is the pure, deterministic half of range-iac: given a LOGICAL RangeSpec and a
PHYSICAL topology plan, produce the exact set of Vultr create-instance / create-VPC /
create-firewall-group / create-firewall-rule requests needed to stand the range up (or
fork it from an existing golden snapshot). No network calls, no provider dependency --
see apply.py for the half that actually talks to a provider.

The one piece of real compiler logic worth calling out (see
docs/adr/ADR-M2-RANGE-PROVISIONING.md and the module docstring in models.py): a
RangeSpec declares LOGICAL reachability between assets (A can reach B on port P); the
topology plan says WHERE each asset physically lives. Only edges that cross a physical
boundary (or originate at INTERNET) need a real Vultr firewall rule -- an edge between
two assets consolidated onto the same physical VM is same-host traffic (e.g. two
containers on one docker-compose network) and compiles to nothing at the Vultr layer.
Getting this right is exactly what matters once GhostScheduler starts moving assets
between physical hosts: the same RangeSpec + a different topology plan must compile to
a different, correct set of firewall rules, with zero edits to the RangeSpec itself.
"""

from __future__ import annotations

from typing import Literal, Optional

from ghostrange_contracts.range import RangeSpecV1
from pydantic import BaseModel

from .cloud_init import render_cloud_init
from .models import INTERNET, PhysicalGroupV1, RangeTopologyPlanV1
from .provider_interface import (
    CompiledRangeInfra,
    FirewallGroupCreateRequest,
    FirewallRuleCreateRequest,
    InstanceCreateRequest,
    VPCCreateRequest,
)

RANGE_VPC_REF = "range-vpc"
RANGE_FW_REF = "range-fw"


class TopologyMismatchError(ValueError):
    """Raised when a RangeSpec and RangeTopologyPlanV1 don't agree with each other."""


class EdgeCompilationRecord(BaseModel):
    """Per-edge compiled-or-not record, returned alongside CompiledRangeInfra so tests
    (and, later, an operator/debugging UI) can see *why* a given edge did or didn't
    produce a Vultr firewall rule."""

    from_asset: str
    to_asset: str
    port: int
    protocol: str
    treatment: Literal[
        "internet_ingress_firewall_rule",
        "cross_host_firewall_rule",
        "same_host_no_rule_needed",
    ]
    firewall_rule: Optional[FirewallRuleCreateRequest] = None


class CompileResult(BaseModel):
    infra: CompiledRangeInfra
    edge_report: list[EdgeCompilationRecord]


def _validate_placement(spec: RangeSpecV1, topology: RangeTopologyPlanV1) -> None:
    if topology.range_spec_id != spec.id:
        raise TopologyMismatchError(
            f"topology.range_spec_id ({topology.range_spec_id}) != rangespec.id ({spec.id})"
        )

    spec_asset_ids = {a.id for a in spec.assets}
    placed_ids: list = []
    for group in topology.physical_groups:
        placed_ids.extend(group.asset_ids)

    placed_set = set(placed_ids)
    if len(placed_ids) != len(placed_set):
        dupes = {i for i in placed_ids if placed_ids.count(i) > 1}
        raise TopologyMismatchError(f"asset(s) placed in more than one physical group: {dupes}")

    missing = spec_asset_ids - placed_set
    if missing:
        raise TopologyMismatchError(f"RangeSpec asset(s) not placed anywhere in topology: {missing}")

    extra = placed_set - spec_asset_ids
    if extra:
        raise TopologyMismatchError(f"topology places unknown asset id(s) not in RangeSpec: {extra}")


def _hostname_to_group(spec: RangeSpecV1, topology: RangeTopologyPlanV1) -> dict[str, PhysicalGroupV1]:
    id_to_hostname = {a.id: a.hostname for a in spec.assets}
    result: dict[str, PhysicalGroupV1] = {}
    for group in topology.physical_groups:
        for asset_id in group.asset_ids:
            hostname = id_to_hostname[asset_id]
            result[hostname] = group
    return result


def _compile_edges(
    spec: RangeSpecV1, topology: RangeTopologyPlanV1
) -> list[EdgeCompilationRecord]:
    hostname_to_group = _hostname_to_group(spec, topology)
    valid_hostnames = set(hostname_to_group)
    records: list[EdgeCompilationRecord] = []

    for edge in topology.edges:
        if edge.from_asset != INTERNET and edge.from_asset not in valid_hostnames:
            raise TopologyMismatchError(f"edge.from_asset '{edge.from_asset}' is not a known asset hostname")
        if edge.to_asset not in valid_hostnames:
            raise TopologyMismatchError(f"edge.to_asset '{edge.to_asset}' is not a known asset hostname")

        to_group = hostname_to_group[edge.to_asset]

        if edge.from_asset == INTERNET:
            rule = FirewallRuleCreateRequest(
                firewall_group_ref=RANGE_FW_REF,
                protocol=edge.protocol,
                port=str(edge.port),
                subnet="0.0.0.0",
                subnet_size=0,
                notes=f"INTERNET -> {edge.to_asset}:{edge.port}/{edge.protocol} ({edge.description})".strip(),
            )
            records.append(
                EdgeCompilationRecord(
                    from_asset=edge.from_asset,
                    to_asset=edge.to_asset,
                    port=edge.port,
                    protocol=edge.protocol,
                    treatment="internet_ingress_firewall_rule",
                    firewall_rule=rule,
                )
            )
            continue

        from_group = hostname_to_group[edge.from_asset]
        if from_group.id == to_group.id:
            records.append(
                EdgeCompilationRecord(
                    from_asset=edge.from_asset,
                    to_asset=edge.to_asset,
                    port=edge.port,
                    protocol=edge.protocol,
                    treatment="same_host_no_rule_needed",
                )
            )
            continue

        # Different physical groups: this edge now genuinely crosses the Vultr
        # network fabric (both groups are attached to the same per-range VPC 2.0,
        # but VPC membership alone is not "reachable" -- Firewall Groups are the
        # allow-list). Source is scoped to the whole VPC subnet rather than a
        # single instance IP because instance IPs aren't known until apply time.
        rule = FirewallRuleCreateRequest(
            firewall_group_ref=RANGE_FW_REF,
            protocol=edge.protocol,
            port=str(edge.port),
            subnet=_vpc_subnet_base(topology),
            subnet_size=_vpc_subnet_size(topology),
            notes=f"{edge.from_asset} -> {edge.to_asset}:{edge.port}/{edge.protocol} ({edge.description})".strip(),
        )
        records.append(
            EdgeCompilationRecord(
                from_asset=edge.from_asset,
                to_asset=edge.to_asset,
                port=edge.port,
                protocol=edge.protocol,
                treatment="cross_host_firewall_rule",
                firewall_rule=rule,
            )
        )

    return records


def _vpc_subnet_base(topology: RangeTopologyPlanV1) -> str:
    # Placeholder until apply.py knows the real VPC 2.0 subnet Vultr assigned;
    # compile-time output only needs to be internally consistent, not a live value.
    return "10.60.0.0"


def _vpc_subnet_size(topology: RangeTopologyPlanV1) -> int:
    return 24


def _derive_public_ip_groups(edge_report: list[EdgeCompilationRecord], hostname_to_group) -> set[str]:
    needs_public: set[str] = set()
    for rec in edge_report:
        if rec.treatment == "internet_ingress_firewall_rule":
            needs_public.add(hostname_to_group[rec.to_asset].id)
    return needs_public


def compile_range(
    spec: RangeSpecV1,
    topology: RangeTopologyPlanV1,
    *,
    mode: Literal["base", "fork"] = "base",
    compose_by_group: dict[str, str],
    support_files_by_group: Optional[dict[str, dict[str, str]]] = None,
    snapshot_map: Optional[dict[str, str]] = None,
) -> CompileResult:
    """Compile a RangeSpec + topology plan into a full provisioning request set.

    Args:
        spec: the LOGICAL RangeSpecV1 (see ranges/ghostrange-auth-lab-v1/rangespec.yaml).
        topology: the PHYSICAL placement + reachability plan (topology.yaml).
        mode: "base" materializes each physical group from a bare os_id (pays the full
            cloud-init cost once); "fork" restores each physical group from an
            already-existing golden snapshot (fast path -- see ADR-006 on why
            snapshot creation itself must never be on this critical path).
        compose_by_group: {PhysicalGroupV1.id -> docker-compose.yml text} for every
            group in the topology. Required for both modes since compose content can
            legitimately differ between a base image build and a fork refresh.
        support_files_by_group: {PhysicalGroupV1.id -> {absolute path -> content}} for
            any files the compose file references (nginx.conf, init.sql, ...).
        snapshot_map: required when mode="fork": {PhysicalGroupV1.id -> snapshot_id}.
            The compiler never creates a snapshot itself -- it only ever *consumes*
            one that was built out of band.
    """
    _validate_placement(spec, topology)

    if mode == "fork" and not snapshot_map:
        raise ValueError("mode='fork' requires snapshot_map={group_id: snapshot_id, ...}")

    hostname_to_group = _hostname_to_group(spec, topology)
    edge_report = _compile_edges(spec, topology)
    public_ip_groups = _derive_public_ip_groups(edge_report, hostname_to_group)

    for group in topology.physical_groups:
        declared = group.needs_public_ip
        derived = group.id in public_ip_groups
        if declared != derived:
            raise TopologyMismatchError(
                f"physical_group '{group.id}'.needs_public_ip={declared} but edges imply "
                f"{derived} (an INTERNET edge targets an asset placed here or not) -- "
                "fix topology.yaml, don't let this drift silently"
            )

    vpc = VPCCreateRequest(
        ref=RANGE_VPC_REF,
        region=topology.physical_groups[0].region,
        description=f"ghostrange range {topology.range_name} ({spec.id})",
        v4_subnet="10.60.0.0",
        v4_subnet_mask=24,
    )
    firewall_group = FirewallGroupCreateRequest(
        ref=RANGE_FW_REF,
        description=f"ghostrange range {topology.range_name} ({spec.id})",
    )
    firewall_rules = [rec.firewall_rule for rec in edge_report if rec.firewall_rule is not None]

    id_to_hostname = {a.id: a.hostname for a in spec.assets}
    support_files_by_group = support_files_by_group or {}

    instances: list[InstanceCreateRequest] = []
    for group in topology.physical_groups:
        placed_hostnames = sorted(id_to_hostname[aid] for aid in group.asset_ids)
        compose_yaml = compose_by_group[group.id]
        support_files = support_files_by_group.get(group.id, {})
        user_data = render_cloud_init(
            compose_yaml=compose_yaml,
            support_files=support_files,
            mode=mode,
        )

        os_id = None
        snapshot_id = None
        if mode == "base":
            os_id = group.os_id
        else:
            snapshot_id = snapshot_map[group.id]  # type: ignore[index]

        instances.append(
            InstanceCreateRequest(
                physical_group_id=group.id,
                hostname=f"{topology.range_name}-{group.id}",
                label=f"{topology.range_name} / {group.id} [{'+'.join(placed_hostnames)}]",
                region=group.region,
                plan=group.plan,
                os_id=os_id,
                snapshot_id=snapshot_id,
                script_id=None,
                user_data=user_data,
                vpc_refs=[RANGE_VPC_REF],
                firewall_group_ref=RANGE_FW_REF,
                disable_public_ipv4=group.id not in public_ip_groups,
                tags=[f"range:{topology.range_name}", f"mode:{mode}"] + [f"asset:{h}" for h in placed_hostnames],
            )
        )

    infra = CompiledRangeInfra(
        range_id=str(spec.id),
        range_name=topology.range_name,
        mode=mode,
        vpc=vpc,
        firewall_group=firewall_group,
        firewall_rules=firewall_rules,
        instances=instances,
    )
    return CompileResult(infra=infra, edge_report=edge_report)


__all__ = ["compile_range", "CompileResult", "EdgeCompilationRecord", "TopologyMismatchError"]
