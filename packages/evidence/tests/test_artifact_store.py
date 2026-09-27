"""ArtifactStore tests: hash computation, immutability end-to-end (raw
bytes -> ArtifactV1 -> object store), tamper detection on read.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest

from ghostrange_contracts.enums import ArtifactType
from ghostrange_evidence.artifact_store import ArtifactStore, compute_content_hash
from ghostrange_evidence.exceptions import ArtifactTamperedError, ObjectIntegrityError
from ghostrange_evidence.object_store import LocalFilesystemObjectStore


def test_compute_content_hash_matches_hashlib():
    data = b"determinism matters"
    assert compute_content_hash(data) == hashlib.sha256(data).hexdigest()


def test_put_bytes_produces_valid_artifact(tmp_path):
    store = ArtifactStore(LocalFilesystemObjectStore(str(tmp_path)))
    world_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    data = b"iptables -L output showing DROP-ALL-INBOUND"

    artifact = store.put_bytes(
        data,
        world_id=world_id,
        artifact_type=ArtifactType.LOG,
        produced_by_execution_id=execution_id,
    )

    assert artifact.world_id == world_id
    assert artifact.produced_by_execution_id == execution_id
    assert artifact.artifact_type == ArtifactType.LOG
    assert artifact.content_hash == hashlib.sha256(data).hexdigest()
    assert artifact.size_bytes == len(data)
    assert artifact.storage_uri.startswith("file://")


def test_get_bytes_roundtrip(tmp_path):
    store = ArtifactStore(LocalFilesystemObjectStore(str(tmp_path)))
    data = b"pcap-like bytes standing in for a real capture"
    artifact = store.put_bytes(
        data, world_id=uuid.uuid4(), artifact_type=ArtifactType.PCAP
    )

    assert store.get_bytes(artifact) == data
    assert store.exists(artifact.content_hash)


def test_identical_bytes_from_different_executions_dedup_at_storage_layer(tmp_path):
    """Two different ExecutionRecords producing byte-identical output
    (e.g. the same boilerplate CALDERA log preamble) should store the
    underlying bytes exactly once, while still getting two distinct
    ArtifactV1 records -- see object_store.py's design-decision docstring
    on why content-addressing (not a hash-chained log) makes this dedup
    free."""
    object_store = LocalFilesystemObjectStore(str(tmp_path))
    store = ArtifactStore(object_store)
    data = b"identical boilerplate log preamble"

    artifact_a = store.put_bytes(
        data, world_id=uuid.uuid4(), artifact_type=ArtifactType.LOG,
        produced_by_execution_id=uuid.uuid4(),
    )
    artifact_b = store.put_bytes(
        data, world_id=uuid.uuid4(), artifact_type=ArtifactType.LOG,
        produced_by_execution_id=uuid.uuid4(),
    )

    assert artifact_a.id != artifact_b.id
    assert artifact_a.content_hash == artifact_b.content_hash
    # Only one physical object was ever written.
    assert object_store.exists(artifact_a.content_hash)


def test_put_bytes_never_overwrites_different_content_at_same_hash(tmp_path):
    """End-to-end version of the immutability guarantee, through the
    ArtifactStore API rather than the raw ObjectStore: if the backing
    store somehow already holds different bytes at the hash key that a
    new artifact's real content hashes to (corruption, or a deliberately
    tampered store), storing must raise rather than silently accept the
    mismatched artifact."""
    object_store = LocalFilesystemObjectStore(str(tmp_path))
    store = ArtifactStore(object_store)
    data = b"the real bytes"
    key = compute_content_hash(data)

    # Simulate corruption: something else wrote different bytes under the
    # key that `data` will hash to (bypassing ArtifactStore entirely).
    object_store.put(key, data)
    corrupt_path = object_store._path_for(key)
    import os

    os.chmod(corrupt_path, 0o644)
    with open(corrupt_path, "wb") as f:
        f.write(b"corrupted bytes with the same key")

    with pytest.raises(ObjectIntegrityError):
        store.put_bytes(data, world_id=uuid.uuid4(), artifact_type=ArtifactType.LOG)


def test_get_bytes_detects_tampered_storage(tmp_path):
    """Read-time tamper-evidence: if the bytes backing an ArtifactV1's
    content_hash have been altered after the fact, get_bytes() must
    detect the mismatch and raise rather than return the wrong bytes."""
    object_store = LocalFilesystemObjectStore(str(tmp_path))
    store = ArtifactStore(object_store)
    artifact = store.put_bytes(
        b"trustworthy bytes", world_id=uuid.uuid4(), artifact_type=ArtifactType.COMMAND_OUTPUT
    )

    # Directly corrupt the file on disk, bypassing the store's own write
    # path (which would refuse this) to simulate e.g. bit rot or an
    # out-of-band modification to the storage backend.
    import os

    path = object_store._path_for(artifact.content_hash)
    os.chmod(path, 0o644)
    with open(path, "wb") as f:
        f.write(b"tampered bytes, different from what was written")

    with pytest.raises(ArtifactTamperedError):
        store.get_bytes(artifact)
