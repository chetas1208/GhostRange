"""Agent 03 — default assumption registry for auth-bypass benchmark."""

from ghostrange_contracts.ghostcausal_m14 import CausalAssumptionKind, CausalAssumptionV1


def default_assumptions() -> list[CausalAssumptionV1]:
    return [
        CausalAssumptionV1(assumption_id="A1", kind=CausalAssumptionKind.TEMPORAL_ORDER, established=True),
        CausalAssumptionV1(
            assumption_id="A2",
            kind=CausalAssumptionKind.NO_UNMEASURED_CONFOUNDING,
            established=False,
            notes="Not established until confounder benchmarks",
        ),
        CausalAssumptionV1(assumption_id="A3", kind=CausalAssumptionKind.MECHANISM_INVARIANCE, established=False),
    ]
