from __future__ import annotations

import hashlib
import json
from typing import Any

from ghostrange_contracts.adversarial_m8 import ObservationNoveltyV1


class NoveltyTracker:
    def __init__(self) -> None:
        self._observation_digests: set[str] = set()

    def score(self, observation: dict[str, Any]) -> ObservationNoveltyV1:
        digest = hashlib.sha256(json.dumps(observation, sort_keys=True).encode()).hexdigest()
        signals: list[str] = []
        if observation.get("status_code") not in (403, 404):
            signals.append("non_standard_status")
        if observation.get("body", {}).get("privileged"):
            signals.append("privileged_body")
        is_novel = digest not in self._observation_digests
        if is_novel:
            self._observation_digests.add(digest)
        score = min(1.0, 0.2 * len(signals) + (0.5 if is_novel else 0.0))
        return ObservationNoveltyV1(score=score, signals=signals, is_novel=is_novel)


__all__ = ["NoveltyTracker"]
