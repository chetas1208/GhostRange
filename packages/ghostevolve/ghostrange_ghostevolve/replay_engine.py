"""Offline replay — what would candidate have predicted/decided?"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class RuntimePredictor(Protocol):
    def predict(self, *, task_class: str, prior_seconds: float) -> float: ...


@dataclass
class ReplayDecision:
    experience_id: str
    champion_prediction: float
    challenger_prediction: float
    actual_seconds: float | None
    off_policy_unknown: bool = False


class EvolutionReplayEngine:
    def replay_runtime_predictions(
        self,
        records: list,
        *,
        champion: RuntimePredictor,
        challenger: RuntimePredictor,
    ) -> list[ReplayDecision]:
        out: list[ReplayDecision] = []
        for rec in records:
            tc = str(rec.context.get("task_class", "default"))
            prior = float(rec.predictions.get("prior_seconds", 30.0))
            actual_raw = rec.actual_outcome.get("runtime_seconds")
            out.append(
                ReplayDecision(
                    experience_id=str(rec.experience_id),
                    champion_prediction=champion.predict(task_class=tc, prior_seconds=prior),
                    challenger_prediction=challenger.predict(task_class=tc, prior_seconds=prior),
                    actual_seconds=float(actual_raw) if actual_raw is not None else None,
                )
            )
        return out

    def counterfactual_note(self, action_never_taken: bool) -> dict[str, Any]:
        if action_never_taken:
            return {"status": "OFF_POLICY_UNKNOWN"}
        return {"status": "OBSERVED"}
