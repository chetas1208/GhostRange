"""Hash-immutability tests for the ObjectStore backends.

Covers: writing new content, idempotent dedup of identical content at the
same key, and the core invariant -- attempting to overwrite existing
content at a given hash with *different* bytes must raise.
"""

from __future__ import annotations

import hashlib

import pytest

from ghostrange_evidence.exceptions import ArtifactNotFoundError, ObjectIntegrityError
from ghostrange_evidence.object_store import LocalFilesystemObjectStore, VultrObjectStorageStore


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# LocalFilesystemObjectStore
# ---------------------------------------------------------------------------


def test_local_store_put_get_roundtrip(tmp_path):
    store = LocalFilesystemObjectStore(str(tmp_path))
    data = b"some log bytes"
    key = _sha256(data)

    store.put(key, data)

    assert store.exists(key)
    assert store.get(key) == data
    assert store.uri_for(key).startswith("file://")


def test_local_store_get_missing_key_raises(tmp_path):
    store = LocalFilesystemObjectStore(str(tmp_path))
    with pytest.raises(ArtifactNotFoundError):
        store.get(_sha256(b"never written"))


def test_local_store_duplicate_write_of_identical_bytes_is_a_noop(tmp_path):
    store = LocalFilesystemObjectStore(str(tmp_path))
    data = b"identical bytes"
    key = _sha256(data)

    store.put(key, data)
    store.put(key, data)  # dedup: must not raise

    assert store.get(key) == data


def test_local_store_refuses_to_overwrite_with_different_bytes(tmp_path):
    """The core hash-immutability guarantee: once `key` holds bytes,
    writing *different* bytes under the same key must raise, never
    silently replace the content."""
    store = LocalFilesystemObjectStore(str(tmp_path))
    key = _sha256(b"original content")
    store.put(key, b"original content")

    with pytest.raises(ObjectIntegrityError):
        # Deliberately mismatched: same key, different payload -- this
        # simulates the "hash collision or corruption" scenario the guard
        # exists for, without needing an actual SHA-256 collision.
        store.put(key, b"a completely different payload")

    # And the original content must be untouched after the failed
    # overwrite attempt.
    assert store.get(key) == b"original content"


def test_local_store_shards_by_key_prefix(tmp_path):
    store = LocalFilesystemObjectStore(str(tmp_path))
    key = _sha256(b"shard test")
    store.put(key, b"shard test")
    path = store._path_for(key)  # internal, but worth asserting the layout
    assert path.endswith(f"/{key[:2]}/{key}")


# ---------------------------------------------------------------------------
# VultrObjectStorageStore, exercised against a hand-written fake S3 client
# (no live Vultr credentials are available in this environment -- see
# object_store.py's module docstring on the gated manual test plan).
# ---------------------------------------------------------------------------


class _FakeS3Client:
    """Implements exactly the subset of the boto3 S3 client surface
    VultrObjectStorageStore calls, backed by an in-memory dict. Good
    enough to exercise the real overwrite-refusal/dedup logic in
    VultrObjectStorageStore itself (which is backend-agnostic Python, not
    boto3-specific) without needing network access or real credentials.
    """

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def head_object(self, Bucket: str, Key: str):
        if (Bucket, Key) not in self.objects:
            raise KeyError(f"no such object: {Bucket}/{Key}")
        return {"ContentLength": len(self.objects[(Bucket, Key)])}

    def get_object(self, Bucket: str, Key: str):
        if (Bucket, Key) not in self.objects:
            raise KeyError(f"no such object: {Bucket}/{Key}")
        data = self.objects[(Bucket, Key)]

        class _Body:
            def __init__(self, payload: bytes) -> None:
                self._payload = payload

            def read(self) -> bytes:
                return self._payload

        return {"Body": _Body(data)}

    def put_object(self, Bucket: str, Key: str, Body: bytes):
        self.objects[(Bucket, Key)] = Body


def test_vultr_store_put_get_via_fake_boto3_client():
    client = _FakeS3Client()
    store = VultrObjectStorageStore(
        bucket="evidence-bucket",
        endpoint_url="https://ewr1.vultrobjects.com",
        client=client,
    )
    data = b"vultr object storage roundtrip bytes"
    key = _sha256(data)

    store.put(key, data)

    assert store.exists(key)
    assert store.get(key) == data
    assert store.uri_for(key) == f"vultr-object-storage://evidence-bucket/artifacts/{key}"


def test_vultr_store_refuses_to_overwrite_with_different_bytes():
    client = _FakeS3Client()
    store = VultrObjectStorageStore(
        bucket="evidence-bucket",
        endpoint_url="https://ewr1.vultrobjects.com",
        client=client,
    )
    key = _sha256(b"original")
    store.put(key, b"original")

    with pytest.raises(ObjectIntegrityError):
        store.put(key, b"different bytes entirely")

    assert store.get(key) == b"original"


def test_vultr_store_get_missing_key_raises():
    client = _FakeS3Client()
    store = VultrObjectStorageStore(
        bucket="evidence-bucket",
        endpoint_url="https://ewr1.vultrobjects.com",
        client=client,
    )
    with pytest.raises(ArtifactNotFoundError):
        store.get(_sha256(b"never written"))


def test_vultr_store_without_boto3_and_no_client_raises_clear_import_error(monkeypatch):
    """No live credentials/boto3 needed to run this suite (see module
    docstring); instantiating without an explicit `client=` when boto3
    genuinely isn't installed should fail loudly and helpfully, not with a
    bare ImportError deep in boto3 internals."""
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "boto3":
            raise ImportError("boto3 not installed (simulated)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    with pytest.raises(ImportError):
        VultrObjectStorageStore(
            bucket="evidence-bucket",
            endpoint_url="https://ewr1.vultrobjects.com",
        )
