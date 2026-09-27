import hashlib
import uuid

import pytest
from pydantic import ValidationError

from ghostrange_contracts.enums import ArtifactType, ObservationType, VerificationMethod
from ghostrange_contracts.evidence import ArtifactV1, ClaimV1, EvidenceV1
from ghostrange_contracts.verification import ObservationV1, VerificationV1


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_valid_artifact_constructs_with_real_hash():
    digest = _sha256(b"some log bytes")
    artifact = ArtifactV1(
        world_id=uuid.uuid4(),
        artifact_type=ArtifactType.LOG,
        storage_uri="vultr-object-storage://evidence/abc.log",
        content_hash=digest,
        size_bytes=14,
    )
    assert artifact.content_hash == digest


def test_artifact_rejects_malformed_hash():
    with pytest.raises(ValidationError):
        ArtifactV1(
            world_id=uuid.uuid4(),
            artifact_type=ArtifactType.LOG,
            storage_uri="vultr-object-storage://evidence/abc.log",
            content_hash="not-a-hash",
            size_bytes=14,
        )


def test_artifact_hash_is_lowercased():
    digest = _sha256(b"case test").upper()
    artifact = ArtifactV1(
        world_id=uuid.uuid4(),
        artifact_type=ArtifactType.LOG,
        storage_uri="vultr-object-storage://evidence/case.log",
        content_hash=digest,
        size_bytes=9,
    )
    assert artifact.content_hash == digest.lower()


def test_claim_confidence_bounds():
    with pytest.raises(ValidationError):
        ClaimV1(
            world_id=uuid.uuid4(),
            statement="CVE-2024-0001 is remediated",
            made_by_agent_id=uuid.uuid4(),
            confidence=1.1,
        )


def test_evidence_chain_end_to_end():
    world_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    observation = ObservationV1(
        execution_id=execution_id,
        world_id=world_id,
        agent_id=agent_id,
        observation_type=ObservationType.LOG_LINE,
        summary="firewall rule DROP-ALL-INBOUND present in iptables output",
    )
    claim = ClaimV1(
        world_id=world_id,
        statement="Remediation closes the exposed RDP port",
        made_by_agent_id=agent_id,
        confidence=0.75,
    )
    verification = VerificationV1(
        claim_id=claim.id,
        world_id=world_id,
        method=VerificationMethod.RE_EXECUTION,
        verifier_agent_id=agent_id,
        observation_ids=[observation.id],
    )
    evidence = EvidenceV1(
        world_id=world_id,
        claim_id=claim.id,
        verification_id=verification.id,
        observation_ids=[observation.id],
        summary="Re-execution confirms port 3389 no longer reachable",
        content_hash=_sha256(b"evidence bundle bytes"),
    )
    assert evidence.claim_id == claim.id
    assert evidence.verification_id == verification.id
    assert observation.id in evidence.observation_ids


def test_evidence_requires_at_least_one_observation():
    with pytest.raises(ValidationError):
        EvidenceV1(
            world_id=uuid.uuid4(),
            claim_id=uuid.uuid4(),
            verification_id=uuid.uuid4(),
            observation_ids=[],
            summary="no observations",
            content_hash=_sha256(b"x"),
        )
