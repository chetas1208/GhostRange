"""Content-addressed artifact store (sha256/ab/abcdef...)."""

from __future__ import annotations

import hashlib
from pathlib import Path


class ContentAddressedArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def digest_bytes(data: bytes) -> str:
        return f"sha256:{hashlib.sha256(data).hexdigest()}"

    def _path_for_digest(self, digest: str) -> Path:
        raw = digest.removeprefix("sha256:")
        return self.root / "sha256" / raw[:2] / raw

    def put(self, data: bytes) -> str:
        digest = self.digest_bytes(data)
        path = self._path_for_digest(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        return digest

    def get(self, digest: str) -> bytes:
        path = self._path_for_digest(digest)
        data = path.read_bytes()
        if self.digest_bytes(data) != digest:
            raise ValueError(f"artifact digest mismatch for {digest}")
        return data

    def exists(self, digest: str) -> bool:
        return self._path_for_digest(digest).exists()


__all__ = ["ContentAddressedArtifactStore"]
