"""M13 GhostMesh API — prepare/publish/receive simulated federation."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass, MeshContributionPolicyV1, MeshDisclosureLevel
from ghostrange_ghostmesh.extract import extract_session_refresh_counterexample
from ghostrange_ghostmesh.harness import GhostMeshHarness, run_m13_demo_story
from ghostrange_ghostmesh.policy_loader import load_mesh_policy

router = APIRouter(prefix="/v1/mesh", tags=["mesh"])

_harness = GhostMeshHarness()
_repo = Path(__file__).resolve().parents[3]


class PrepareBody(BaseModel):
    tenant_label: str = "org-a"
    enable_sharing: bool = True


class PublishBody(BaseModel):
    node_id: str = "A"


@router.get("/policy")
async def get_policy():
    return load_mesh_policy(_repo / "config" / "mesh-contribution-policy.yaml").model_dump(mode="json")


@router.post("/contributions/prepare")
async def prepare_contribution(body: PrepareBody):
    pol_path = _repo / "config" / "mesh-contribution-policy.yaml"
    policy = load_mesh_policy(pol_path)
    if body.enable_sharing:
        policy = MeshContributionPolicyV1(
            sharing_enabled=True,
            allowed_knowledge_classes=[KnowledgeClass.COUNTEREXAMPLE_PATTERN],
            minimum_local_validations=1,
            minimum_abstraction_tags=2,
            default_disclosure=MeshDisclosureLevel.PSEUDONYMOUS_STRUCTURED,
            require_human_approval=False,
            allowed_federation_ids=["bench-consortium"],
        )
    node = _harness.nodes.get("A")
    if not node:
        raise HTTPException(500, "harness node A missing")
    node.policy = policy
    cand = extract_session_refresh_counterexample(local_source_ref="api:prepare", tenant_label=body.tenant_label)
    result = node.prepare_contribution(cand)
    if not result.ok:
        raise HTTPException(400, detail={"reason": result.reason})
    return {
        "contribution": result.contribution.model_dump(mode="json"),
        "privacy_profile": result.privacy_profile.model_dump(mode="json") if result.privacy_profile else None,
        "label": "SIMULATED_MESH",
    }


@router.post("/contributions/publish")
async def publish_contribution(body: PublishBody):
    node = _harness.nodes.get(body.node_id)
    if not node:
        raise HTTPException(404, "unknown node")
    prep = node.prepare_contribution(
        extract_session_refresh_counterexample(local_source_ref="api:publish", tenant_label="org-a")
    )
    if not prep.ok or not prep.contribution:
        raise HTTPException(400, prep.reason)
    ok = _harness.coordinator_publish(body.node_id, prep.contribution)
    if ok:
        _harness.deliver_to_all(prep.contribution)
    return {"published": ok, "contribution_id": str(prep.contribution.id), "label": "SIMULATED_MESH"}


@router.get("/knowledge")
async def list_knowledge(node_id: str = "B"):
    node = _harness.nodes.get(node_id)
    if not node:
        raise HTTPException(404, "unknown node")
    return {
        "node_id": node_id,
        "contributions": [c.model_dump(mode="json") for c in node.registry.contributions.values()],
        "receipts": [r.model_dump(mode="json") for r in node.receipts],
        "label": "SIMULATED_MESH",
    }


@router.post("/knowledge/{contribution_id}/evaluate")
async def evaluate_knowledge(contribution_id: str, node_id: str = "B"):
    node = _harness.nodes.get(node_id)
    if not node:
        raise HTTPException(404, "unknown node")
    rep = node.evaluate(contribution_id)
    if not rep:
        raise HTTPException(404, "contribution not on node")
    return rep.model_dump(mode="json")


class ValidateBody(BaseModel):
    node_id: str = "B"
    confirmed: bool = True


@router.post("/knowledge/{contribution_id}/validate-local")
async def validate_local(contribution_id: str, body: ValidateBody):
    node = _harness.nodes.get(body.node_id)
    if not node:
        raise HTTPException(404, "unknown node")
    status = node.validate_local(contribution_id, confirmed=body.confirmed)
    ex = node.director_experiments(contribution_id)
    return {
        "status": status.value,
        "experiments": [e.__dict__ for e in ex],
        "label": "SIMULATED_MESH",
    }


@router.post("/demo/story")
async def demo_story():
    r = run_m13_demo_story()
    return {**r.__dict__, "status": {k: getattr(v, "value", v) for k, v in r.__dict__.items()}}


class RevokeBody(BaseModel):
    node_id: str = "A"
    reason: str = "operator_revocation"


@router.post("/revocations")
async def post_revocation(contribution_id: str, body: RevokeBody):
    from ghostrange_ghostmesh.revocation import revoke_contribution

    coord = _harness.coordinator
    if not coord or contribution_id not in coord.registry.contributions:
        raise HTTPException(404, "contribution not found")
    from uuid import UUID

    rev = revoke_contribution(
        coord.registry,
        contribution_id=UUID(contribution_id),
        revoker_node_id=body.node_id,
        reason=body.reason,
    )
    return {"revoked": True, "revocation": rev.model_dump(mode="json")}


@router.get("/analytics/cohort")
async def cohort_analytics(kclass: str = "COUNTEREXAMPLE_PATTERN", min_cohort: int = 3):
    from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass
    from ghostrange_ghostmesh.federated_analytics import cohort_validation_rate

    coord = _harness.coordinator
    if not coord:
        raise HTTPException(500, "coordinator missing")
    out = cohort_validation_rate(coord.registry, KnowledgeClass(kclass), min_cohort=min_cohort)
    if not out:
        return {"released": False, "reason": "MINIMUM_COHORT_NOT_MET"}
    return {"released": True, **out}
