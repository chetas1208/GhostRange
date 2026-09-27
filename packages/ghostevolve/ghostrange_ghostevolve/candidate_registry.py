"""Champion / challenger registry with immutable promoted history."""

from __future__ import annotations

from ghostrange_contracts.ghostevolve_m18 import (
    EvolutionCandidateState,
    EvolutionCandidateV1,
    LearningSurface,
)


class EvolutionCandidateRegistry:
    def __init__(self) -> None:
        self._champions: dict[LearningSurface, str] = {
            LearningSurface.SCHEDULER_RUNTIME_ESTIMATOR: "runtime-estimator:v4-m15",
        }
        self._candidates: dict[str, EvolutionCandidateV1] = {}
        self._history: list[str] = list(self._champions.values())

    def champion_version(self, surface: LearningSurface) -> str:
        return self._champions.get(surface, "unknown")

    def register(self, candidate: EvolutionCandidateV1) -> EvolutionCandidateV1:
        self._candidates[candidate.candidate_digest()] = candidate
        return candidate

    def transition(self, candidate: EvolutionCandidateV1, state: EvolutionCandidateState) -> EvolutionCandidateV1:
        updated = candidate.model_copy(update={"state": state})
        self._candidates[updated.candidate_digest()] = updated
        return updated

    def promote(self, candidate: EvolutionCandidateV1) -> None:
        if candidate.state not in (EvolutionCandidateState.CANARY, EvolutionCandidateState.SHADOW):
            raise ValueError("promote only after canary/shadow pipeline")
        self._champions[candidate.learning_surface] = candidate.version_label
        self._history.append(candidate.version_label)
        self.transition(candidate, EvolutionCandidateState.PROMOTED)

    def rollback_to(self, surface: LearningSurface, version: str) -> None:
        if version not in self._history:
            raise ValueError("rollback target not preserved in champion history")
        self._champions[surface] = version
