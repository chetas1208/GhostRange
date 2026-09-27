"""Postgres metadata + Vultr Object Storage bytes."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from ghostrange_evidence.object_store import VultrObjectStorageStore
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import Settings


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: uuid.UUID
    case_id: uuid.UUID
    object_key: str
    sha256: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class ArtifactRegistry:
    def __init__(self, pool: AsyncConnectionPool, object_store: VultrObjectStorageStore) -> None:
        self._pool = pool
        self._store = object_store

    @classmethod
    def from_settings(cls, pool: AsyncConnectionPool, settings: Settings) -> "ArtifactRegistry":
        from .ops_routes import object_store_from_settings

        return cls(pool, object_store_from_settings(settings))

    async def store_artifact(
        self,
        *,
        case_id: uuid.UUID,
        data: bytes,
        mime_type: str = "application/octet-stream",
        artifact_id: uuid.UUID | None = None,
    ) -> ArtifactRecord:
        sha = hashlib.sha256(data).hexdigest()
        aid = artifact_id or uuid.uuid4()
        self._store.put(sha, data)
        object_key = self._store._object_key(sha)  # noqa: SLF001
        now = datetime.now(timezone.utc)
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO artifact_registry (
                        artifact_id, case_id, object_key, sha256, mime_type, size_bytes, created_at, updated_at
                    ) VALUES (%(artifact_id)s, %(case_id)s, %(object_key)s, %(sha256)s, %(mime_type)s,
                              %(size_bytes)s, %(created_at)s, %(updated_at)s)
                    ON CONFLICT (artifact_id) DO UPDATE SET
                        object_key = EXCLUDED.object_key,
                        sha256 = EXCLUDED.sha256,
                        mime_type = EXCLUDED.mime_type,
                        size_bytes = EXCLUDED.size_bytes,
                        updated_at = EXCLUDED.updated_at
                    """,
                    {
                        "artifact_id": aid,
                        "case_id": case_id,
                        "object_key": object_key,
                        "sha256": sha,
                        "mime_type": mime_type,
                        "size_bytes": len(data),
                        "created_at": now,
                        "updated_at": now,
                    },
                )
        return ArtifactRecord(
            artifact_id=aid,
            case_id=case_id,
            object_key=object_key,
            sha256=sha,
            mime_type=mime_type,
            size_bytes=len(data),
            created_at=now,
            updated_at=now,
        )

    async def get_artifact(self, artifact_id: uuid.UUID) -> tuple[ArtifactRecord, bytes]:
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM artifact_registry WHERE artifact_id = %(id)s",
                    {"id": artifact_id},
                )
                row = await cur.fetchone()
        if not row:
            raise KeyError(f"artifact {artifact_id} not found")
        data = self._store.get(row["sha256"])
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise RuntimeError("artifact checksum mismatch")
        rec = ArtifactRecord(
            artifact_id=row["artifact_id"],
            case_id=row["case_id"],
            object_key=row["object_key"],
            sha256=row["sha256"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        return rec, data

    async def update_artifact(
        self, artifact_id: uuid.UUID, data: bytes, mime_type: str | None = None
    ) -> ArtifactRecord:
        rec, _ = await self.get_artifact(artifact_id)
        return await self.store_artifact(
            case_id=rec.case_id,
            data=data,
            mime_type=mime_type or rec.mime_type,
            artifact_id=artifact_id,
        )
