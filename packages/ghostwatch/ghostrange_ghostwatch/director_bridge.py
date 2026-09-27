"""Production surprise → disposable-world experiment proposal (never prod)."""

from __future__ import annotations

from dataclasses import dataclass

from ghostrange_contracts.ghostwatch_m12 import ProductionSurpriseV1


@dataclass
class DisposableExperimentProposal:
    title: str
    rationale: str
    run_in: str = "GHOSTRANGE_DISPOSABLE_WORLD"


def propose_from_surprise(surprise: ProductionSurpriseV1) -> DisposableExperimentProposal:
    return DisposableExperimentProposal(
        title="Reproduce auth-path divergence in range",
        rationale=f"Production surprise: {surprise.description}. Director must NOT experiment on production.",
    )
