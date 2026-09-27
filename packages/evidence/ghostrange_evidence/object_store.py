"""Content-addressed key/value object storage backends.

## Design decision: content-addressed storage, not a hash-chained log

``docs/architecture/EVIDENCE.md`` flags this as the open question owned by
this package: should Artifact bytes live in a content-addressed store
(dedup by hash, globally) or an append-only, hash-chained log (each entry
references the hash of the previous entry, per World)?

**Decision: content-addressed, keyed directly by the ``content_hash`` that
``ArtifactV1`` already validates (SHA-256, 64-char lowercase hex).**

Why, concretely, for this system rather than in the abstract:

1. ``ArtifactV1.content_hash`` already exists, is already validated at
   construction (``evidence.py::_validate_hash_format``), and is already
   the field every other package (events, provenance queries, the Evidence
   3D view) will key off of. A hash-chained log would need a *second*,
   parallel identifier (this-entry-depends-on-previous-entry-hash) that
   nothing else in the contract layer expects or consumes — it would be
   pure additional surface area with no consumer.
2. Tamper-evidence is already inherent to content-addressing: any bytes
   that don't hash to their claimed ``content_hash`` are provably invalid
   on read, independent of *when* they were written or what else was
   written before/after them. A hash chain's extra guarantee — "the whole
   sequence of writes to this log is unmodified" — answers a question
   GhostRange doesn't ask. Nothing in the product ever needs to prove "no
   artifact was deleted from World X's evidence log between t1 and t2";
   every consumer (Verification, Observation, the 3D view) asks "is *this
   specific* Artifact, referenced by *this specific* id, still what it
   claims to be" — a per-object question, not a log-integrity question.
3. Dedup is free and actually matters here: the same golden-snapshot base
   image, the same CALDERA technique's boilerplate log preamble, or the
   same "auth service returned 401" response body will recur across many
   Worlds/Executions in a controlled scenario like
   ``ghostrange-auth-lab-v1``, which forks Worlds specifically to compare
   remediations side by side. A hash-chained log stores each occurrence
   once per World by construction (that's what "chained" means); content
   addressing stores the distinct bytes exactly once, globally, which is
   the cheaper and simpler property given (1) and (2) above don't need the
   log's extra guarantee.
4. It composes trivially with Vultr Object Storage's S3-compatible API
   (docs/research/VULTR.md §7, ADOPTed there for exactly this purpose):
   the content_hash *is* the object key. No separate index of
   "chain position -> object key" needs to be maintained and kept
   consistent with the object store.

Trade-off accepted: content-addressed storage alone does not, by itself,
prove *when* an artifact was first written or that nothing was ever
deleted from a World's evidence set. If GhostRange later needs that
stronger guarantee (e.g. for a compliance audit trail rather than
per-claim verification), the fix is additive -- an append-only *index* of
"artifact_id written at time T for World W" on top of this store, not a
replacement of it. That index is exactly what ``ProvenanceStore``
(``provenance.py``) already is: an ordered record of what was registered
and when, backed by whatever durable store (Postgres, per
docs/research/VULTR.md's "Postgres holds metadata/pointers, not the blobs
themselves") replaces the in-memory dict used here for M2 scope.

## Backends

- ``LocalFilesystemObjectStore``: sharded, git-object-style layout
  (``<root>/<algo>/<hash[:2]>/<hash>``), no external dependency. This is
  what tests run against and what local/CI dev uses.
- ``VultrObjectStorageStore``: talks to Vultr Object Storage's
  S3-compatible endpoint (docs/research/VULTR.md §7) via ``boto3``,
  keyed the same way. ``boto3`` is an optional dependency
  (``pip install "ghostrange-evidence[vultr]"``); importing this module
  never requires it, only *instantiating* this specific class does, so
  the rest of the package works in an environment with no live Vultr
  credentials -- mirroring how ``packages/vultr-control`` (Agent 02) is
  expected to degrade to a mock/no-op provider without live credentials.
  There is no live-credential test for this backend in this package's
  test suite (none are available in this environment); it is exercised
  by ``tests/test_object_store.py::test_vultr_store_put_get_via_fake_boto3_client``
  against a hand-written fake S3 client that implements the subset of the
  boto3 S3 client surface this class calls, and is intended to also be run
  as a gated manual smoke test against a real bucket per
  docs/research/VULTR.md's own testing plan for this integration
  ("A gated manual test confirms a real upload/download round-trip against
  a real Object Storage bucket").
"""

from __future__ import annotations

import os
import tempfile
from typing import Protocol, runtime_checkable

from .exceptions import ArtifactNotFoundError, ObjectIntegrityError


@runtime_checkable
class ObjectStore(Protocol):
    """Minimal content-addressed key/value store.

    ``key`` is always the hex content-hash of ``data`` under whatever hash
    algorithm the caller (``ArtifactStore``) used to compute it; this
    protocol itself is hash-algorithm-agnostic and never computes hashes
    -- that is deliberately the ``ArtifactStore`` layer's job, so this
    layer stays a dumb, swappable, immutable blob store.
    """

    def put(self, key: str, data: bytes) -> None:
        """Write ``data`` under ``key``.

        Idempotent no-op if ``key`` already exists and its stored bytes
        are identical to ``data``. Raises ``ObjectIntegrityError`` if
        ``key`` already exists with *different* bytes -- this is the
        "never allow overwriting existing content at a given hash"
        requirement, enforced at the lowest layer so every
        ``ArtifactStore`` backend gets it for free.
        """
        ...

    def get(self, key: str) -> bytes:
        """Return the bytes stored under ``key``.

        Raises ``ArtifactNotFoundError`` if ``key`` is not present.
        """
        ...

    def exists(self, key: str) -> bool: ...

    def uri_for(self, key: str) -> str:
        """Return the ``storage_uri`` this backend would put on an
        ``ArtifactV1`` for ``key`` (e.g. ``file://...`` or
        ``vultr-object-storage://bucket/key``)."""
        ...


class LocalFilesystemObjectStore:
    """Filesystem-backed :class:`ObjectStore`, sharded like git objects
    (``<root>/<hash[:2]>/<hash>``) so a single directory never accumulates
    an unbounded number of entries.

    Write path uses exclusive create (``os.O_CREAT | os.O_EXCL``) so two
    concurrent writers racing to write the *same* key can't corrupt each
    other's write -- the loser simply falls through to the
    already-exists-compare-bytes path below, which is the same path taken
    by a non-racing duplicate write (dedup).
    """

    def __init__(self, root_dir: str) -> None:
        self.root_dir = os.path.abspath(root_dir)
        os.makedirs(self.root_dir, exist_ok=True)

    def _path_for(self, key: str) -> str:
        key = key.lower()
        shard = key[:2] if len(key) >= 2 else "__"
        return os.path.join(self.root_dir, shard, key)

    def put(self, key: str, data: bytes) -> None:
        path = self._path_for(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing = self.get(key)
            if existing != data:
                raise ObjectIntegrityError(
                    f"refusing to overwrite existing object at key '{key}': "
                    f"stored content ({len(existing)} bytes) differs from "
                    f"new content ({len(data)} bytes)"
                )
            return  # idempotent dedup: identical bytes already stored
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            # Don't leave a partially-written file claiming to hold `key`'s
            # content.
            try:
                os.remove(path)
            except OSError:
                pass
            raise
        # Immutable from here on: strip write permission from owner/group/
        # other. Best-effort -- some filesystems/CI sandboxes may not honor
        # chmod, which is fine, `put`'s own exclusive-create + compare logic
        # is the real enforcement point, this is defense-in-depth.
        try:
            os.chmod(path, 0o444)
        except OSError:
            pass

    def get(self, key: str) -> bytes:
        path = self._path_for(key)
        try:
            with open(path, "rb") as f:
                return f.read()
        except FileNotFoundError as exc:
            raise ArtifactNotFoundError(f"no object stored at key '{key}'") from exc

    def exists(self, key: str) -> bool:
        return os.path.isfile(self._path_for(key))

    def uri_for(self, key: str) -> str:
        return f"file://{self._path_for(key)}"


def make_temp_local_object_store() -> LocalFilesystemObjectStore:
    """Convenience for tests/dev: a fresh, isolated local store under the
    system temp dir."""
    return LocalFilesystemObjectStore(tempfile.mkdtemp(prefix="ghostrange-evidence-"))


class VultrObjectStorageStore:
    """:class:`ObjectStore` backed by Vultr Object Storage's S3-compatible
    API (docs/research/VULTR.md §7).

    Not exercised against live credentials in this package's automated
    tests (none are configured in this environment) -- see the module
    docstring. Any object exposing the subset of the ``boto3`` S3 client
    surface used below (``head_object``, ``get_object``, ``put_object``)
    can be passed as ``client``, which is what lets the test suite exercise
    the real logic (existence-check, compare-before-refusing-to-overwrite,
    key layout) against a hand-written fake instead of skipping it
    outright.
    """

    def __init__(
        self,
        bucket: str,
        *,
        endpoint_url: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        key_prefix: str = "artifacts/",
        client: object | None = None,
    ) -> None:
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.key_prefix = key_prefix
        if client is not None:
            self._client = client
        else:
            try:
                import boto3  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover - exercised via fake client in tests
                raise ImportError(
                    "VultrObjectStorageStore requires boto3 to talk to a real "
                    "Vultr Object Storage endpoint. Install with "
                    "`pip install 'ghostrange-evidence[vultr]'`, or pass an "
                    "explicit `client=` (e.g. a test double) if you don't "
                    "need a real connection."
                ) from exc
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )

    def _object_key(self, key: str) -> str:
        return f"{self.key_prefix}{key.lower()}"

    def exists(self, key: str) -> bool:
        object_key = self._object_key(key)
        try:
            self._client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except Exception:
            # botocore raises a ClientError subclass with a 404 response for
            # a missing key; a fake test client may raise a plain KeyError/
            # generic Exception instead. Either way, "not found" is the only
            # reachable failure mode of head_object in normal operation --
            # anything else (auth failure, network) will also surface loudly
            # from the subsequent get/put call, so treating any exception
            # here as "doesn't exist yet" is safe and keeps this method
            # dependency-free of botocore's specific exception hierarchy.
            return False

    def put(self, key: str, data: bytes) -> None:
        object_key = self._object_key(key)
        if self.exists(key):
            existing = self.get(key)
            if existing != data:
                raise ObjectIntegrityError(
                    f"refusing to overwrite existing object at key '{key}' "
                    f"in bucket '{self.bucket}': stored content "
                    f"({len(existing)} bytes) differs from new content "
                    f"({len(data)} bytes)"
                )
            return  # idempotent dedup
        self._client.put_object(Bucket=self.bucket, Key=object_key, Body=data)

    def get(self, key: str) -> bytes:
        object_key = self._object_key(key)
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=object_key)
        except Exception as exc:
            raise ArtifactNotFoundError(
                f"no object stored at key '{key}' in bucket '{self.bucket}'"
            ) from exc
        body = response["Body"]
        return body.read() if hasattr(body, "read") else bytes(body)

    def uri_for(self, key: str) -> str:
        return f"vultr-object-storage://{self.bucket}/{self._object_key(key)}"


__all__ = [
    "ObjectStore",
    "LocalFilesystemObjectStore",
    "VultrObjectStorageStore",
    "make_temp_local_object_store",
]
