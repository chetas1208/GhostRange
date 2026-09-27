"""Placement — consolidate logical services onto VMs when fidelity allows."""

from __future__ import annotations

import hashlib

from ghostrange_contracts.fidelity_m5 import FidelityProfileV1, FidelityDimension, FidelityRequirementLevel
from ghostrange_contracts.system_graph import GraphNodeKind, NormalizedSystemGraphV1
from ghostrange_contracts.twin_compiler import PlacementAlternativeV1, PlacementPlanV1


def plan_placement(
    blueprint_id,
    graph: NormalizedSystemGraphV1,
    profile: FidelityProfileV1,
) -> PlacementPlanV1:
    services = [n for n in graph.nodes if n.kind in (GraphNodeKind.SERVICE, GraphNodeKind.GATEWAY, GraphNodeKind.DATABASE)]
    names = sorted(n.name for n in services)
    resource_req = profile.dimensions.get(FidelityDimension.RESOURCE, FidelityRequirementLevel.OPTIONAL)
    vm_count = 1 if resource_req != FidelityRequirementLevel.REQUIRED else max(1, min(len(names), 3))

    asset_to_vm: dict[str, str] = {}
    for i, name in enumerate(names):
        vm = f"vm-{(i % vm_count) + 1}"
        asset_to_vm[name] = vm

    consolidated = PlacementAlternativeV1(
        label="consolidated",
        vm_count=1,
        estimated_hourly_cost_usd=0.05,
        resource_fidelity_score=0.64,
        explanation="Resource fidelity OPTIONAL — consolidated all services onto one VM",
    )
    distributed = PlacementAlternativeV1(
        label="distributed",
        vm_count=len(names),
        estimated_hourly_cost_usd=0.05 * len(names),
        resource_fidelity_score=0.95,
        explanation="One VM per service — higher resource/network isolation fidelity",
    )
    selected = consolidated if vm_count == 1 else distributed
    ph = hashlib.sha256(str(sorted(asset_to_vm.items())).encode()).hexdigest()[:16]

    return PlacementPlanV1(
        blueprint_id=blueprint_id,
        selected_vm_count=selected.vm_count,
        asset_to_vm=asset_to_vm,
        alternatives=[consolidated, distributed],
        estimated_hourly_cost_usd=selected.estimated_hourly_cost_usd,
        estimated_startup_seconds=120.0,
        placement_hash=ph,
        explanation=selected.explanation,
    )


__all__ = ["plan_placement"]
