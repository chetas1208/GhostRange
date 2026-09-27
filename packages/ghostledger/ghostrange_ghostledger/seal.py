"""Seal experiment → root → attestation → bundle."""

from __future__ import annotations

from uuid import uuid4

from ghostrange_contracts.ghostledger_m7 import (
    BundleMode,
    DisclosurePolicyV1,
    ExperimentAttestationV1,
    ExperimentDefinitionV1,
    ExperimentIDV1,
    ExperimentManifestV1,
    ExperimentRootV1,
    GhostBundleV1,
    GhostRangeExperimentPredicateV1,
    ProvenanceEdgeKind,
    ProvenanceGraphV1,
    ProvenanceNodeKind,
    ProvenanceNodeV1,
    ProvenanceEdgeV1,
    ReplayLevel,
    SigningIdentityKind,
    ArtifactIndexEntryV1,
)

from .canonical import digest_sha256
from .event_chain import chain_events
from .merkle import merkle_root
from .signing import DevSigner


def _minimal_manifest(**overrides) -> ExperimentManifestV1:
    exp_id = ExperimentIDV1(
        definition=ExperimentDefinitionV1(
            definition_id="auth-remediation-v1",
            title="Auth remediation verification",
            description="M7 fixture experiment",
        ),
    )
    base = {
        "experiment": exp_id,
        "source_revision_id": uuid4(),
        "source_hash": "sha256:" + "a" * 64,
        "twin_revision_id": uuid4(),
        "twin_fingerprint": "fp-auth-lab-1",
        "range_spec_hash": "sha256:" + "b" * 64,
        "compiler_version": "range-compiler/v0.1",
        "fidelity_profile_id": uuid4(),
        "investigation_objective": "auth_remediation",
        "initiator": "operator@ghostrange.local",
    }
    base.update(overrides)
    return ExperimentManifestV1(**base)


def graph_content_digest(graph: ProvenanceGraphV1) -> str:
    body = graph.model_dump(mode="json")
    body.pop("graph_digest", None)
    return digest_sha256(body)


def build_provenance_graph(manifest: ExperimentManifestV1) -> ProvenanceGraphV1:
    nodes = [
        ProvenanceNodeV1(kind=ProvenanceNodeKind.SOURCE_REVISION, ref_id=str(manifest.source_revision_id), label="source"),
        ProvenanceNodeV1(kind=ProvenanceNodeKind.TWIN_REVISION, ref_id=str(manifest.twin_revision_id), label="twin"),
        ProvenanceNodeV1(kind=ProvenanceNodeKind.EXPERIMENT, ref_id=str(manifest.experiment.run_id), label="experiment"),
    ]
    edges = [
        ProvenanceEdgeV1(from_node_id=nodes[2].id, to_node_id=nodes[1].id, kind=ProvenanceEdgeKind.DERIVED_FROM),
        ProvenanceEdgeV1(from_node_id=nodes[1].id, to_node_id=nodes[0].id, kind=ProvenanceEdgeKind.DERIVED_FROM),
    ]
    g = ProvenanceGraphV1(experiment_run_id=manifest.experiment.run_id, nodes=nodes, edges=edges)
    return g.model_copy(update={"graph_digest": graph_content_digest(g)})


def seal_experiment(
    manifest: ExperimentManifestV1,
    *,
    signer: DevSigner,
    artifact_digests: list[str] | None = None,
    raw_events: list[dict] | None = None,
    claims_digest: str | None = None,
    mode: BundleMode = BundleMode.FULL,
) -> tuple[GhostBundleV1, str]:
    """Returns bundle and signer public PEM for verifier trust store."""
    graph = build_provenance_graph(manifest)
    artifact_digests = artifact_digests or []
    chained, event_root = chain_events(raw_events or [{"type": "experiment.started"}])
    claims_digest = claims_digest or digest_sha256({"claims": []})

    manifest_d = digest_sha256(manifest)
    graph_d = graph.graph_digest or graph_content_digest(graph)
    artifact_root = merkle_root(artifact_digests)

    root_body = {
        "manifest_digest": manifest_d,
        "provenance_graph_digest": graph_d,
        "artifact_merkle_root": artifact_root,
        "event_log_root": event_root,
        "claim_set_digest": claims_digest,
    }
    root_digest = digest_sha256(root_body)
    experiment_root = ExperimentRootV1(
        manifest_digest=manifest_d,
        provenance_graph_digest=graph_d,
        artifact_merkle_root=artifact_root,
        event_log_root=event_root,
        claim_set_digest=claims_digest,
        root_digest=root_digest,
    )

    predicate = GhostRangeExperimentPredicateV1(
        experiment_root=experiment_root,
        manifest_id=manifest.manifest_id,
    )
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": "experiment-root", "digest": {"sha256": root_digest.removeprefix("sha256:")}}],
        "predicateType": predicate.predicate_type,
        "predicate": predicate.model_dump(mode="json"),
    }
    sig = signer.sign_payload(statement)

    attestation = ExperimentAttestationV1(
        subject_digest=root_digest,
        predicate=predicate,
        signature_b64=sig,
        key_id=signer.key_id,
        signer_kind=SigningIdentityKind.LOCAL_DEVELOPMENT,
        payload_type="application/vnd.ghostrange.experimentpredicate+json",
    )

    index = [
        ArtifactIndexEntryV1(logical_name=f"artifact-{i}", digest=d, size_bytes=0)
        for i, d in enumerate(artifact_digests)
    ]

    bundle = GhostBundleV1(
        mode=mode,
        manifest=manifest,
        provenance_graph=graph,
        experiment_root=experiment_root,
        attestation=attestation,
        artifact_index=index,
        event_log=chained,
        claims_digest=claims_digest,
        replay_level=ReplayLevel.LEVEL_4,
        disclosure=DisclosurePolicyV1(),
    )
    bundle = bundle.model_copy(update={"bundle_digest": digest_sha256(bundle.model_dump(mode="json"))})
    return bundle, signer.public_key_pem()


__all__ = ["seal_experiment", "build_provenance_graph", "_minimal_manifest"]
