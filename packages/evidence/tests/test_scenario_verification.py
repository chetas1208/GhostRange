"""Determinism and rule-correctness tests for the ghostrange-auth-lab-v1
deterministic verification function.
"""

from __future__ import annotations

import uuid

from ghostrange_contracts.enums import ObservationType, VerificationResult
from ghostrange_contracts.verification import ObservationV1
from ghostrange_evidence.scenario_verification import (
    AuthLabVerdict,
    evaluate_auth_lab_v1,
    verdict_to_verification_result,
)


def _observation(summary: str, observation_type: ObservationType = ObservationType.COMMAND_RESULT) -> ObservationV1:
    return ObservationV1(
        execution_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        observation_type=observation_type,
        summary=summary,
    )


def test_rejection_only_observations_yield_expected_condition_observed():
    observations = [
        _observation("POST /login with bad-credential returned HTTP 401 Unauthorized"),
        _observation("auth service log: authentication failed for probe account"),
    ]

    result = evaluate_auth_lab_v1(observations)

    assert result.verdict == AuthLabVerdict.EXPECTED_CONDITION_OBSERVED
    assert len(result.rejection_matches) == 2
    assert result.permissive_matches == ()


def test_permissive_observation_yields_expected_condition_not_observed():
    observations = [
        _observation("POST /login with known-bad credential returned HTTP/1.1 200 OK, login successful"),
    ]

    result = evaluate_auth_lab_v1(observations)

    assert result.verdict == AuthLabVerdict.EXPECTED_CONDITION_NOT_OBSERVED
    assert len(result.permissive_matches) == 1


def test_single_permissive_counterexample_outweighs_many_rejections():
    """A single unexpectedly-permissive response must sink the verdict
    even alongside many observations showing correct rejection -- mirrors
    EVIDENCE.md's worked example where one successful attack observation
    flips a PASSED verification to FAILED."""
    observations = [
        _observation("HTTP 401 Unauthorized returned for bad credential attempt #1"),
        _observation("HTTP 403 Forbidden returned for bad credential attempt #2"),
        _observation("access denied for bad credential attempt #3"),
        _observation("HTTP/1.1 200 OK -- access granted for bad credential attempt #4 (regression)"),
    ]

    result = evaluate_auth_lab_v1(observations)

    assert result.verdict == AuthLabVerdict.EXPECTED_CONDITION_NOT_OBSERVED
    assert len(result.rejection_matches) == 3
    assert len(result.permissive_matches) == 1


def test_no_matching_observations_is_inconclusive():
    observations = [
        _observation("agent noted the service appeared to be running", ObservationType.AGENT_ASSERTION),
    ]

    result = evaluate_auth_lab_v1(observations)

    assert result.verdict == AuthLabVerdict.INCONCLUSIVE


def test_empty_observation_list_is_inconclusive():
    result = evaluate_auth_lab_v1([])
    assert result.verdict == AuthLabVerdict.INCONCLUSIVE
    assert result.considered_observation_ids == ()


def test_verdict_is_deterministic():
    """Same input list -> same verdict, every time, and the function must
    not mutate its input. This is the concrete guarantee that ground
    truth here is a pure rule evaluation, not anything with hidden state
    or a model call that could vary run to run."""
    observations = [
        _observation("HTTP 401 Unauthorized for bad credential"),
        _observation("HTTP/1.1 200 OK login successful for bad credential (bug)"),
        _observation("firewall log: unrelated entry"),
    ]
    snapshot = list(observations)

    results = [evaluate_auth_lab_v1(observations) for _ in range(25)]

    assert all(r.verdict == results[0].verdict for r in results)
    assert results[0].verdict == AuthLabVerdict.EXPECTED_CONDITION_NOT_OBSERVED
    # input untouched
    assert observations == snapshot


def test_verdict_to_verification_result_mapping():
    assert verdict_to_verification_result(AuthLabVerdict.EXPECTED_CONDITION_OBSERVED) == VerificationResult.PASSED
    assert verdict_to_verification_result(AuthLabVerdict.EXPECTED_CONDITION_NOT_OBSERVED) == VerificationResult.FAILED
    assert verdict_to_verification_result(AuthLabVerdict.INCONCLUSIVE) == VerificationResult.INCONCLUSIVE


def test_case_insensitive_matching():
    observations = [_observation("post /login -> unauthorized (bad credential rejected)")]
    result = evaluate_auth_lab_v1(observations)
    assert result.verdict == AuthLabVerdict.EXPECTED_CONDITION_OBSERVED
