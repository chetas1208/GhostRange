from __future__ import annotations

from ghostrange_contracts.adversarial_m8 import SearchMemoryEntryV1, SearchMemoryV1, ObservationNoveltyV1, SearchArmKind


class SearchMemory:
    def __init__(self, search_run_id) -> None:
        self.search_run_id = search_run_id
        self._seen: set[str] = set()
        self.entries: list[SearchMemoryEntryV1] = []

    def seen(self, fingerprint: str) -> bool:
        return fingerprint in self._seen

    def record(
        self,
        fingerprint: str,
        arm: SearchArmKind,
        result: str,
        observation_digest: str,
        *,
        cost_usd: float = 0.0,
        novelty: ObservationNoveltyV1 | None = None,
    ) -> None:
        self._seen.add(fingerprint)
        self.entries.append(
            SearchMemoryEntryV1(
                candidate_fingerprint=fingerprint,
                arm=arm,
                result=result,
                observation_digest=observation_digest,
                cost_usd=cost_usd,
                novelty=novelty or ObservationNoveltyV1(score=0.0),
            )
        )

    def to_model(self) -> SearchMemoryV1:
        return SearchMemoryV1(search_run_id=self.search_run_id, entries=list(self.entries))


__all__ = ["SearchMemory"]
