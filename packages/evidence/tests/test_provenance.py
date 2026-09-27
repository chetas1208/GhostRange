"""ProvenanceStore tests: full chain traversal correctness (mirroring
EVIDENCE.md's worked example), and the structural guarantee that a claim
with zero evidence cannot be marked verified.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest

from ghostrange_contracts.enums import (
    ArtifactType,
    ExecutionStatus,
    ObservationType,
    VerificationMethod,
    VerificationResult,
    WorldStatus,
)
from ghostrange_contracts.evidence import ArtifactV1, ClaimV1, EvidenceV1
from ghostrange_contracts.execution_graph import ExecutionRecordV1
from ghostrange_contracts.verification import ObservationV1, VerificationV1
from ghostrange_contracts.world import WorldV1
from ghostrange_evidence.exceptions import NoEvidenceError, UnknownReferenceError
from ghostrange_evidence.provenance import ClaimVerificationStatus, ProvenanceStore


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_worked_example_chain():
    """Reconstructs docs/architecture/EVIDENCE.md's 7-step worked example:
    remediation closes RDP port 3389, an adversary's re-attack is
    observed refusing the connection, verification PASSES, evidence
    bundles it all together."""
    range_id = uuid.uuid4()
    world = WorldV1(range_id=range_id, label="remediation-a", status=WorldStatus.VERIFYING)

    agent_id = uuid.uuid4()
    claim = ClaimV1(
        world_id=world.id,
        statement="Remediation closes the exposed RDP port",
        made_by_agent_id=agent_id,
        confidence=0.75,
    )

    execution = ExecutionRecordV1(
        task_id=uuid.uuid4(),
        world_id=world.id,
        agent_id=agent_id,
        command="attack --technique T1021.001 --target dc01:3389",
        status=ExecutionStatus.SUCCEEDED,
        exit_code=0,
    )

    pcap_bytes = b"fake pcap bytes: connection attempt to 3389 refused"
    pcap_artifact = ArtifactV1(
        world_id=world.id,
        produced_by_execution_id=execution.id,
        artifact_type=ArtifactType.PCAP,
        storage_uri="vultr-object-storage://evidence/rdp-attempt.pcap",
        content_hash=_sha256(pcap_bytes),
        size_bytes=len(pcap_bytes),
    )
    execution.artifact_ids = [pcap_artifact.id]

    observation = ObservationV1(
        execution_id=execution.id,
        world_id=world.id,
        agent_id=agent_id,
        observation_type=ObservationType.NETWORK_TRAFFIC,
        summary="connection attempt to 3389 refused",
        raw_artifact_id=pcap_artifact.id,
    )

    verification = VerificationV1(
        claim_id=claim.id,
        world_id=world.id,
        method=VerificationMethod.ADVERSARIAL_ATTACK,
        verifier_agent_id=agent_id,
        observation_ids=[observation.id],
        result=VerificationResult.PASSED,
    )

    evidence = EvidenceV1(
        world_id=world.id,
        claim_id=claim.id,
        verification_id=verification.id,
        observation_ids=[observation.id],
        artifact_ids=[pcap_artifact.id],
        summary="Adversarial re-attack confirms port 3389 no longer reachable",
        content_hash=_sha256(b"evidence bundle bytes for this worked example"),
    )

    store = ProvenanceStore()
    store.register_world(world)
    store.register_execution_record(execution)
    store.register_artifact(pcap_artifact)
    store.register_observation(observation)
    store.register_verification(verification)
    store.register_claim(claim)
    store.register_evidence(evidence)

    return {
        "store": store,
        "world": world,
        "claim": claim,
        "execution": execution,
        "pcap_artifact": pcap_artifact,
        "observation": observation,
        "verification": verification,
        "evidence": evidence,
    }


# ---------------------------------------------------------------------------
# Full chain traversal
# ---------------------------------------------------------------------------


def test_full_provenance_chain_traversal_correctness():
    ctx = _build_worked_example_chain()
    store: ProvenanceStore = ctx["store"]

    chain = store.get_provenance_chain(ctx["claim"].id)

    assert chain.claim.id == ctx["claim"].id
    assert len(chain.evidence) == 1

    ev_link = chain.evidence[0]
    assert ev_link.evidence.id == ctx["evidence"].id
    assert ev_link.verification is not None
    assert ev_link.verification.id == ctx["verification"].id
    assert ev_link.verification.result == VerificationResult.PASSED
    assert len(ev_link.bundle_artifacts) == 1
    assert ev_link.bundle_artifacts[0].id == ctx["pcap_artifact"].id

    assert len(ev_link.observations) == 1
    obs_link = ev_link.observations[0]
    assert obs_link.observation.id == ctx["observation"].id
    assert obs_link.execution_record is not None
    assert obs_link.execution_record.id == ctx["execution"].id
    assert obs_link.world is not None
    assert obs_link.world.id == ctx["world"].id
    # The pcap artifact is reachable both via the ExecutionRecord's
    # artifact_ids and the Observation's own raw_artifact_id -- must
    # appear exactly once, not duplicated.
    assert [a.id for a in obs_link.artifacts] == [ctx["pcap_artifact"].id]


def test_provenance_chain_for_claim_with_no_evidence_yet_is_empty_not_an_error():
    store = ProvenanceStore()
    claim = ClaimV1(
        world_id=uuid.uuid4(),
        statement="Unverified claim, no evidence registered",
        made_by_agent_id=uuid.uuid4(),
        confidence=0.5,
    )
    store.register_claim(claim)

    chain = store.get_provenance_chain(claim.id)

    assert chain.claim.id == claim.id
    assert chain.evidence == ()
    assert chain.verification_status == ClaimVerificationStatus.UNVERIFIED


def test_provenance_chain_for_unregistered_claim_raises():
    store = ProvenanceStore()
    with pytest.raises(UnknownReferenceError):
        store.get_provenance_chain(uuid.uuid4())


def test_dangling_reference_raises_distinctly():
    """An Evidence bundle whose verification_id doesn't resolve to any
    registered VerificationV1 is a data-integrity bug, not a "no evidence"
    state -- must raise UnknownReferenceError, distinct from NoEvidenceError."""
    store = ProvenanceStore()
    claim = ClaimV1(
        world_id=uuid.uuid4(),
        statement="claim with a dangling evidence reference",
        made_by_agent_id=uuid.uuid4(),
        confidence=0.5,
    )
    store.register_claim(claim)

    dangling_observation_id = uuid.uuid4()
    evidence = EvidenceV1(
        world_id=claim.world_id,
        claim_id=claim.id,
        verification_id=uuid.uuid4(),  # never registered
        observation_ids=[dangling_observation_id],  # never registered
        summary="references records that don't exist",
        content_hash=_sha256(b"dangling"),
    )
    store.register_evidence(evidence)

    with pytest.raises(UnknownReferenceError):
        store.get_provenance_chain(claim.id)


# ---------------------------------------------------------------------------
# Claim verification gating: zero evidence -> structurally cannot verify
# ---------------------------------------------------------------------------


def test_claim_with_zero_evidence_cannot_be_marked_verified():
    store = ProvenanceStore()
    claim = ClaimV1(
        world_id=uuid.uuid4(),
        statement="A claim nobody has ever verified",
        made_by_agent_id=uuid.uuid4(),
        confidence=0.9,
    )
    store.register_claim(claim)

    with pytest.raises(NoEvidenceError):
        store.mark_claim_verified(claim.id)

    # And the status must remain UNVERIFIED -- the failed attempt must not
    # have side-effected the claim into looking verified.
    assert store.get_claim_status(claim.id) == ClaimVerificationStatus.UNVERIFIED


def test_mark_claim_verified_on_unregistered_claim_raises():
    store = ProvenanceStore()
    with pytest.raises(UnknownReferenceError):
        store.mark_claim_verified(uuid.uuid4())


def test_claim_with_passed_verification_evidence_becomes_verified():
    ctx = _build_worked_example_chain()
    store: ProvenanceStore = ctx["store"]

    status = store.mark_claim_verified(ctx["claim"].id)

    assert status == ClaimVerificationStatus.VERIFIED
    assert store.get_claim_status(ctx["claim"].id) == ClaimVerificationStatus.VERIFIED
    # And that status is visible through the chain query too.
    chain = store.get_provenance_chain(ctx["claim"].id)
    assert chain.verification_status == ClaimVerificationStatus.VERIFIED


def test_claim_with_failed_verification_becomes_refuted():
    ctx = _build_worked_example_chain()
    store: ProvenanceStore = ctx["store"]
    ctx["verification"].result = VerificationResult.FAILED

    status = store.mark_claim_verified(ctx["claim"].id)

    assert status == ClaimVerificationStatus.REFUTED


def test_claim_with_only_pending_verification_stays_unverified():
    ctx = _build_worked_example_chain()
    store: ProvenanceStore = ctx["store"]
    ctx["verification"].result = VerificationResult.PENDING

    status = store.mark_claim_verified(ctx["claim"].id)

    assert status == ClaimVerificationStatus.UNVERIFIED
