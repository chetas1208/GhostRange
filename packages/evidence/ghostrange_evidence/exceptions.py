"""Exceptions raised by ghostrange_evidence.

Kept in one module so callers (packages/scheduler, apps/api, adversary
adapters, tests) can catch a stable, documented set of failure modes
instead of bare ``Exception`` or storage-backend-specific errors leaking
across the package boundary.
"""

from __future__ import annotations


class GhostRangeEvidenceError(Exception):
    """Base class for all errors raised by this package."""


class ObjectIntegrityError(GhostRangeEvidenceError):
    """Raised when a write to a content-addressed key would overwrite
    existing bytes with *different* bytes.

    This should be unreachable in practice (it requires either a SHA-256
    collision or on-disk/bucket corruption of previously-written content),
    but the guard exists precisely so that "should be unreachable" is an
    enforced invariant rather than an assumption. Enforced at the
    ``ObjectStore`` layer, so every ``ArtifactStore`` backend inherits the
    same immutability guarantee for free.
    """


class ArtifactNotFoundError(GhostRangeEvidenceError):
    """Raised when reading back an artifact whose content-hash key is not
    present in the backing object store."""


class ArtifactTamperedError(GhostRangeEvidenceError):
    """Raised when bytes read back from storage for a given content_hash
    key do not re-hash to that same content_hash.

    This is the read-time half of tamper-evidence promised in
    docs/architecture/EVIDENCE.md: "if an Artifact ... is later re-fetched
    from storage_uri and its hash no longer matches content_hash, the
    evidence is provably invalid." Every ``ArtifactStore.get_bytes()`` call
    re-verifies this rather than trusting the stored metadata.
    """


class NoEvidenceError(GhostRangeEvidenceError):
    """Raised by claim-verification-marking logic when a Claim has zero
    EvidenceV1 bundles (or an EvidenceV1 bundle with zero observations
    slipped in through an untrusted/pre-validation path).

    This is the concrete enforcement of "a claim with zero evidence must be
    structurally unable to be marked verified" at the packages/evidence
    layer, mirroring (defense-in-depth, not duplicating trust in) the
    ``EvidenceV1.observation_ids`` ``min_length=1`` constraint already
    enforced by ``packages/contracts`` at construction time.
    """


class UnknownReferenceError(GhostRangeEvidenceError):
    """Raised when a provenance query is asked to traverse a reference
    (e.g. ``EvidenceV1.claim_id``, ``ObservationV1.execution_id``) that does
    not resolve to any record registered in the ``ProvenanceStore``.

    Surfacing this as a distinct, catchable error (rather than a bare
    ``KeyError``) matters because a dangling reference in the evidence
    chain is itself evidence-relevant information (a data integrity bug,
    not a "this claim simply has no evidence yet" state), and callers
    (e.g. the Evidence 3D view) may want to render it differently.
    """
