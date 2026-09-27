"""ghostrange_evidence: artifact storage, deterministic scenario
verification, and provenance-chain queries backing GhostRange's
Claim -> Verification -> Observation -> Execution -> World -> Artifact
evidence chain (see docs/architecture/EVIDENCE.md).

This package owns the *implementation* behind the contracts already
defined in ``ghostrange_contracts`` (``ClaimV1``, ``EvidenceV1``,
``ArtifactV1``, ``ObservationV1``, ``VerificationV1``): where artifact
bytes actually live, how a claim's evidence is actually queried end to
end, and how the M2 controlled scenario's expected-condition check is
actually decided (deterministically, never by asking a model).

Quick map:

- ``object_store``: content-addressed key/value blob storage
  (``LocalFilesystemObjectStore`` for local/CI, ``VultrObjectStorageStore``
  targeting Vultr Object Storage's S3-compatible API).
- ``artifact_store``: ``ArtifactStore`` -- raw bytes in, immutable
  ``ArtifactV1`` out; never allows overwriting existing content at a given
  hash; re-verifies hash on every read.
- ``scenario_verification``: deterministic, rule-based verdict logic for
  ``ghostrange-auth-lab-v1`` (``evaluate_auth_lab_v1``).
- ``provenance``: ``ProvenanceStore`` -- register evidence-chain records,
  traverse the full chain for a Claim (``get_provenance_chain``), and gate
  claim-verification on real evidence existing (``mark_claim_verified``).
"""

from .artifact_store import ArtifactStore, compute_content_hash
from .exceptions import (
    ArtifactNotFoundError,
    ArtifactTamperedError,
    GhostRangeEvidenceError,
    NoEvidenceError,
    ObjectIntegrityError,
    UnknownReferenceError,
)
from .object_store import (
    LocalFilesystemObjectStore,
    ObjectStore,
    VultrObjectStorageStore,
    make_temp_local_object_store,
)
from .provenance import (
    ClaimVerificationStatus,
    EvidenceChainLink,
    ObservationChainLink,
    ProvenanceChain,
    ProvenanceStore,
)
from .scenario_verification import (
    AuthLabVerdict,
    AuthLabVerdictResult,
    ObservationMatch,
    evaluate_auth_lab_v1,
    verdict_to_verification_result,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # object_store
    "ObjectStore",
    "LocalFilesystemObjectStore",
    "VultrObjectStorageStore",
    "make_temp_local_object_store",
    # artifact_store
    "ArtifactStore",
    "compute_content_hash",
    # scenario_verification
    "AuthLabVerdict",
    "AuthLabVerdictResult",
    "ObservationMatch",
    "evaluate_auth_lab_v1",
    "verdict_to_verification_result",
    # provenance
    "ProvenanceStore",
    "ProvenanceChain",
    "EvidenceChainLink",
    "ObservationChainLink",
    "ClaimVerificationStatus",
    # exceptions
    "GhostRangeEvidenceError",
    "ObjectIntegrityError",
    "ArtifactNotFoundError",
    "ArtifactTamperedError",
    "NoEvidenceError",
    "UnknownReferenceError",
]
