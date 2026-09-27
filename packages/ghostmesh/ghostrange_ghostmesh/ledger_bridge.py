"""Agent 30 — mesh provenance lineage (local in-memory; not full M7 seal)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MeshProvenanceEntry:
    kind: str
    digest: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class MeshProvenanceLog:
    entries: list[MeshProvenanceEntry] = field(default_factory=list)

    def record(self, kind: str, digest: str, **detail: Any) -> None:
        self.entries.append(MeshProvenanceEntry(kind=kind, digest=digest, detail=detail))

    def audit_questions(self) -> dict[str, bool]:
        kinds = {e.kind for e in self.entries}
        return {
            "extraction_recorded": "mesh.contribution_extracted" in kinds,
            "privacy_transform_recorded": "mesh.contribution_privacy_checked" in kinds,
            "share_recorded": "mesh.contribution_published" in kinds,
            "receipt_recorded": "mesh.contribution_received" in kinds,
            "local_validation_recorded": any(k.startswith("mesh.local_validation") for k in kinds),
        }
