from __future__ import annotations

from uuid import uuid4

from ghostrange_contracts.adversarial_m8 import (
    CounterexampleV1,
    VerificationSuiteRevisionV1,
    VerificationTestSource,
)

from .mutations import candidate_fingerprint


def promote_counterexample_to_regression(
    counterexample: CounterexampleV1,
    *,
    suite_id=None,
) -> VerificationSuiteRevisionV1:
    return VerificationSuiteRevisionV1(
        suite_id=suite_id or uuid4(),
        added_from=VerificationTestSource.COUNTEREXAMPLE,
        counterexample_id=counterexample.id,
        test_fingerprint=candidate_fingerprint({"sequence": counterexample.action_sequence}),
    )


__all__ = ["promote_counterexample_to_regression"]
