"""Runtime estimation — first M18 learning surface (low authority)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from ghostrange_contracts.ghostevolve_m18 import ExperienceRecordV1


@dataclass
class M15RuntimeEstimatorChampion:
    """Baseline: fixed inflation factor over context prior (M15-style estimate)."""

    version_label: str = "runtime-estimator:v4-m15"
    inflation: float = 1.35

    def predict(self, *, task_class: str, prior_seconds: float) -> float:
        base = prior_seconds if prior_seconds > 0 else 30.0
        if task_class == "cpu_benchmark":
            base = max(base, 25.0)
        return base * self.inflation


@dataclass
class RuntimeEstimatorCandidate:
    """EWMA per task class from verified experiences."""

    version_label: str = "runtime-estimator:v5"
    alpha: float = 0.35
    class_means: dict[str, float] = field(default_factory=dict)
    feature_revision: str = "runtime-features/v1"

    def train(self, records: list[ExperienceRecordV1]) -> None:
        for rec in sorted(records, key=lambda r: r.recorded_at):
            tc = str(rec.context.get("task_class", "default"))
            actual = float(rec.actual_outcome.get("runtime_seconds", 0))
            if actual <= 0:
                continue
            prev = self.class_means.get(tc, actual)
            self.class_means[tc] = (1 - self.alpha) * prev + self.alpha * actual

    def predict(self, *, task_class: str, prior_seconds: float) -> float:
        if task_class in self.class_means:
            return self.class_means[task_class]
        return prior_seconds if prior_seconds > 0 else 30.0

    def artifact_digest(self) -> str:
        payload = {
            "version_label": self.version_label,
            "class_means": self.class_means,
            "feature_revision": self.feature_revision,
            "alpha": self.alpha,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
