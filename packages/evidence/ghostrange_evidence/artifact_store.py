"""ArtifactStore: turn raw bytes into an immutable, content-addressed
``ArtifactV1`` (packages/contracts/ghostrange_contracts/evidence.py).

This is the concrete implementation of EVIDENCE.md's ARTIFACT leaf node:
"concrete, content-addressed bytes (a log file, a pcap, a screenshot)
stored in object storage, referenced by hash for tamper-evidence."

Usage::

    store = ArtifactStore(LocalFilesystemObjectStore("/var/ghostrange/evidence"))
    artifact = store.put_bytes(
        response_bytes,
        world_id=world.id,
        artifact_type=ArtifactType.COMMAND_OUTPUT,
        produced_by_execution_id=execution.id,
    )
    # later, from anywhere holding just the ArtifactV1:
    raw = store.get_bytes(artifact)  # re-verifies hash on read
"""

from __future__ import annotations

import hashlib
import uuid

from ghostrange_contracts.enums import ArtifactType, HashAlgorithm
from ghostrange_contracts.evidence import ArtifactV1

from .exceptions import ArtifactTamperedError
from .object_store import ObjectStore

_HASHERS = {
    HashAlgorithm.SHA256: hashlib.sha256,
}


def compute_content_hash(data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
    """Hex digest of ``data`` under ``algorithm``. The single place this
    package computes a content hash, so ``ArtifactStore`` and any test
    asserting hash-immutability behavior agree on exactly one
    implementation."""
    hasher = _HASHERS[algorithm]()
    hasher.update(data)
    return hasher.hexdigest()


class ArtifactStore:
    """Content-addressed artifact persistence: raw bytes in, immutable
    ``ArtifactV1`` out.

    Two calls to :meth:`put_bytes` with identical bytes (even for
    different ``world_id``/``artifact_type`` combinations) dedup at the
    object-storage layer -- see ``object_store.py`` module docstring for
    why that's the deliberate design, not an accident. They still produce
    *two distinct* ``ArtifactV1`` records (different ``id``, possibly
    different ``world_id``/``produced_by_execution_id``), because an
    Artifact's identity in the evidence chain is "this specific execution
    produced/referenced these bytes", not just "these bytes exist
    somewhere" -- ``content_hash`` is what's deduplicated, not the
    Artifact record itself.
    """

    def __init__(self, object_store: ObjectStore) -> None:
        self._object_store = object_store

    def put_bytes(
        self,
        data: bytes,
        *,
        world_id: uuid.UUID,
        artifact_type: ArtifactType,
        produced_by_execution_id: uuid.UUID | None = None,
        hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256,
    ) -> ArtifactV1:
        """Hash ``data``, store it immutably (never overwriting distinct
        content at the same hash -- enforced by the underlying
        ``ObjectStore``), and return the ``ArtifactV1`` describing it.
        """
        content_hash = compute_content_hash(data, hash_algorithm)
        self._object_store.put(content_hash, data)  # raises ObjectIntegrityError on tamper/collision
        storage_uri = self._object_store.uri_for(content_hash)
        return ArtifactV1(
            world_id=world_id,
            produced_by_execution_id=produced_by_execution_id,
            artifact_type=artifact_type,
            storage_uri=storage_uri,
            hash_algorithm=hash_algorithm,
            content_hash=content_hash,
            size_bytes=len(data),
        )

    def get_bytes(self, artifact: ArtifactV1) -> bytes:
        """Fetch back the raw bytes for ``artifact``, re-verifying the
        hash on read.

        This is the read-time half of tamper-evidence: metadata saying
        "this artifact's hash is X" is never trusted on its own -- the
        bytes actually retrieved from storage must re-hash to X, every
        time. If they don't, the evidence is provably invalid and we
        raise rather than silently returning bytes that no longer match
        the record a Claim/Observation/Verification points at.
        """
        data = self._object_store.get(artifact.content_hash)
        recomputed = compute_content_hash(data, artifact.hash_algorithm)
        if recomputed != artifact.content_hash:
            raise ArtifactTamperedError(
                f"artifact {artifact.id}: stored bytes hash to "
                f"'{recomputed}' but ArtifactV1.content_hash is "
                f"'{artifact.content_hash}'"
            )
        return data

    def exists(self, content_hash: str) -> bool:
        return self._object_store.exists(content_hash.lower())


__all__ = ["ArtifactStore", "compute_content_hash"]
