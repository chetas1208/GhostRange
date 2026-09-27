"""GhostExperienceStore — immutable raw records + indexed metadata (in-memory v1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ghostrange_contracts.ghostevolve_m18 import ExperienceRecordV1, LearningEligibility, LearningSurface

from .eligibility import classify_experience_eligibility


class GhostExperienceStore:
    def __init__(self, *, persist_path: Path | None = None) -> None:
        self._records: dict[str, ExperienceRecordV1] = {}
        self._persist_path = persist_path

    def append(self, record: ExperienceRecordV1) -> ExperienceRecordV1:
        elig = classify_experience_eligibility(record)
        digest = record.compute_immutable_digest()
        stored = record.model_copy(
            update={
                "learning_eligibility": elig,
                "immutable_raw_digest": digest,
            }
        )
        self._records[str(stored.experience_id)] = stored
        self._maybe_persist()
        return stored

    def get(self, experience_id: str) -> ExperienceRecordV1 | None:
        return self._records.get(experience_id)

    def list_eligible(
        self,
        *,
        surface: LearningSurface | None = None,
        eligibility: Iterable[LearningEligibility] | None = None,
    ) -> list[ExperienceRecordV1]:
        allowed = set(eligibility or (LearningEligibility.ELIGIBLE, LearningEligibility.ELIGIBLE_WITH_LIMITATIONS))
        out: list[ExperienceRecordV1] = []
        for rec in sorted(self._records.values(), key=lambda r: r.recorded_at):
            if rec.learning_eligibility not in allowed:
                continue
            if surface == LearningSurface.SCHEDULER_RUNTIME_ESTIMATOR:
                if rec.actual_outcome.get("runtime_seconds") is None:
                    continue
            out.append(rec)
        return out

    def _maybe_persist(self) -> None:
        if not self._persist_path:
            return
        payload = [json.loads(r.model_dump_json()) for r in self._records.values()]
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> GhostExperienceStore:
        store = cls(persist_path=path)
        if not path.exists():
            return store
        for item in json.loads(path.read_text(encoding="utf-8")):
            rec = ExperienceRecordV1.model_validate(item)
            store._records[str(rec.experience_id)] = rec
        return store
