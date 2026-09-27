"""Rule-based investigation → fidelity profile (no LLM authority)."""

from __future__ import annotations

from ghostrange_contracts.fidelity_m5 import (
    FidelityDimension,
    FidelityProfileV1,
    FidelityRequirementLevel,
    InvestigationObjectiveV1,
)


def profile_for_objective(objective: InvestigationObjectiveV1) -> FidelityProfileV1:
    dims: dict[FidelityDimension, FidelityRequirementLevel] = {}
    kind = objective.investigation_kind
    if kind in ("auth_remediation", "authentication", "auth"):
        dims = {
            FidelityDimension.TOPOLOGY: FidelityRequirementLevel.REQUIRED,
            FidelityDimension.NETWORK: FidelityRequirementLevel.REQUIRED,
            FidelityDimension.SERVICE: FidelityRequirementLevel.REQUIRED,
            FidelityDimension.CONFIGURATION: FidelityRequirementLevel.REQUIRED,
            FidelityDimension.IDENTITY: FidelityRequirementLevel.REQUIRED,
            FidelityDimension.DATA_SCHEMA: FidelityRequirementLevel.IMPORTANT,
            FidelityDimension.RESOURCE: FidelityRequirementLevel.OPTIONAL,
            FidelityDimension.TIMING: FidelityRequirementLevel.IGNORED,
        }
    else:
        dims = {
            FidelityDimension.TOPOLOGY: FidelityRequirementLevel.REQUIRED,
            FidelityDimension.SERVICE: FidelityRequirementLevel.IMPORTANT,
            FidelityDimension.RESOURCE: FidelityRequirementLevel.OPTIONAL,
        }
    return FidelityProfileV1(objective_id=objective.id, dimensions=dims)


__all__ = ["profile_for_objective"]
