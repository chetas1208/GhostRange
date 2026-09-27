"""Emit RangeSpecV2 from blueprint + placement (logical assets)."""

from __future__ import annotations

from uuid import uuid4

from ghostrange_contracts.enums import AssetRole, SecurityCriticality
from ghostrange_contracts.range import AssetSpecV1, NetworkSpecV1
from ghostrange_contracts.range_v2 import RangeSpecV2
from ghostrange_contracts.twin_compiler import CompilationManifestV1, PlacementPlanV1, TwinBlueprintV1


def _role_for_service(name: str) -> AssetRole:
    if "gateway" in name.lower():
        return AssetRole.LOAD_BALANCER
    if "data" in name.lower() or "postgres" in name.lower() or name.lower() == "db":
        return AssetRole.DATABASE
    if "auth" in name.lower():
        return AssetRole.SERVER
    return AssetRole.SERVER


def blueprint_to_rangespec_v2(
    blueprint: TwinBlueprintV1,
    placement: PlacementPlanV1,
    manifest: CompilationManifestV1,
    *,
    owner: str,
    name: str,
) -> RangeSpecV2:
    net = NetworkSpecV1(name="twin-net", cidr="10.42.0.0/24", description="Compiled twin network")
    assets: list[AssetSpecV1] = []
    for svc in blueprint.required_services:
        assets.append(
            AssetSpecV1(
                hostname=svc,
                network_id=net.id,
                os_family="linux",
                role=_role_for_service(svc),
                image=blueprint.service_images.get(svc, "container"),
                criticality=SecurityCriticality.MEDIUM,
            )
        )
    return RangeSpecV2(
        name=name,
        description=f"Compiled twin revision {blueprint.revision}",
        owner=owner,
        networks=[net],
        assets=assets,
        twin_blueprint_id=blueprint.id,
        placement_plan_id=placement.id,
        compilation_manifest_id=manifest.id,
        source_graph_hash=manifest.blueprint_hash,
        compiled_from_revision=blueprint.revision,
        tags={"compiler": manifest.compiler_version},
    )


__all__ = ["blueprint_to_rangespec_v2"]
