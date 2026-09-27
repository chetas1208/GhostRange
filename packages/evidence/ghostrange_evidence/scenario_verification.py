"""Deterministic, rule-based verification for M2's controlled scenario,
``ghostrange-auth-lab-v1``.

## Explicitly not an LLM judgment call

Ground truth in this module is a pure function of structured
``ObservationV1`` data: string/pattern matching against
``ObservationV1.summary`` plus ``ObservationV1.observation_type``, nothing
else. No model is ever asked "did this work?" here. A model MAY be used
elsewhere (e.g. summarizing a verdict and its evidence for a human reading
the Evidence 3D view), but it is never the thing that *decides* the
verdict -- see :func:`evaluate_auth_lab_v1` and
:func:`verdict_is_deterministic_smoke_test` below for why this matters
operationally, not just as a principle: the same input list of
Observations must produce the same verdict every time, forever, including
after a model version bump -- which is only guaranteed if no model is in
the decision path at all.

## ASSUMPTION -- to confirm with Agent 06 (controlled scenario engineer)

As of this writing, ``ranges/ghostrange-auth-lab-v1/`` is empty -- Agent 06
(wave 2) had not started when this module was written. Rather than block
on that, this module encodes a concrete, reasonable assumption about the
scenario's shape, stated explicitly so it can be confirmed or corrected
once Agent 06's actual harness lands:

    ASSUMPTION: ``ghostrange-auth-lab-v1`` provisions an authentication
    service (e.g. an HTTP login endpoint) reachable from the executing
    agent's World. The scenario's tested security condition is:

        "A request to the auth service using a known-bad/invalid
        credential is correctly rejected -- no session/token is issued,
        no success response is returned."

    The EXPECTED (secure/remediated) outcome is REJECTION of the
    bad-credential attempt. The scenario is specifically probing for
    regressions where the service is *unexpectedly permissive* (accepts a
    credential it should reject) -- e.g. an auth bypass, a broken
    comparison, a default-allow misconfiguration.

    Observations relevant to this scenario are expected to arrive as
    ``COMMAND_RESULT`` (e.g. curl/CALDERA output), ``NETWORK_TRAFFIC``
    (e.g. a captured HTTP response), or ``LOG_LINE`` (e.g. the auth
    service's own request log) with a ``summary`` that is a short natural-
    language/structured description containing recognizable markers of
    either outcome (see ``_PERMISSIVE_MARKERS`` / ``_REJECTION_MARKERS``
    below). ``AGENT_ASSERTION`` observations are accepted but weighted no
    differently at the *rule* level -- ``EVIDENCE.md`` already flags that
    an assertion with no backing artifact carries lower evidentiary
    *weight*, which is a presentation/confidence concern for
    ``EvidenceV1``/the UI, not something this deterministic gate applies
    inconsistently; this function's job is only "is there a positive rule
    match", not confidence-weighting.

    If Agent 06's real harness tags observations differently (e.g. a
    structured field instead of free text, or additional
    ``ObservationType`` values), the fix is to keep this module's *verdict
    logic* (single-counterexample-wins, in :func:`evaluate_auth_lab_v1`)
    and swap the marker-matching in :func:`_classify` for whatever the
    real structured shape is -- the interface
    (``Sequence[ObservationV1] -> AuthLabVerdict``) should not need to
    change.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from ghostrange_contracts.enums import VerificationResult
from ghostrange_contracts.verification import ObservationV1


class AuthLabVerdict(str, Enum):
    """The deterministic verdict for a `ghostrange-auth-lab-v1` check.

    Named to match the vocabulary requested for this scenario type
    (EXPECTED_CONDITION_OBSERVED / EXPECTED_CONDITION_NOT_OBSERVED), plus
    an explicit third state for "the observations given don't say either
    way" -- returning a false positive/negative by defaulting an
    inconclusive case to one of the two definite verdicts would be worse
    than being honest that the rule set had nothing to match.
    """

    EXPECTED_CONDITION_OBSERVED = "EXPECTED_CONDITION_OBSERVED"
    EXPECTED_CONDITION_NOT_OBSERVED = "EXPECTED_CONDITION_NOT_OBSERVED"
    INCONCLUSIVE = "INCONCLUSIVE"


# Deterministic keyword/pattern rules. Case-insensitive literal matching
# only -- no fuzzy matching, no embeddings, no model call. Ordering within
# each tuple is irrelevant (all are checked); ordering of the two tuples
# relative to each other matters in `_classify`'s priority (permissive
# checked first -- see `evaluate_auth_lab_v1` docstring on why a single
# counterexample wins).
_PERMISSIVE_MARKERS: tuple[str, ...] = (
    "200 ok",
    "http/1.1 200",
    "http/2 200",
    "authenticated successfully",
    "authentication successful",
    "login successful",
    "login succeeded",
    "session token issued",
    "session created",
    "access granted",
    "auth succeeded",
    "authorization successful",
)

_REJECTION_MARKERS: tuple[str, ...] = (
    "401",
    "403",
    "unauthorized",
    "forbidden",
    "authentication failed",
    "auth failed",
    "access denied",
    "invalid credentials",
    "invalid password",
    "login failed",
    "login rejected",
    "credentials rejected",
    "request rejected",
)

def _matches(summary: str, markers: tuple[str, ...]) -> list[str]:
    """Return the subset of `markers` literally present in `summary`
    (case-insensitive substring match). Deterministic and order-preserving
    for auditability (the caller can show *which* phrase matched)."""
    lowered = summary.lower()
    return [m for m in markers if m in lowered]


@dataclass(frozen=True)
class ObservationMatch:
    """One Observation's classification, kept for the rationale trail."""

    observation_id: uuid.UUID
    matched_permissive: tuple[str, ...] = field(default_factory=tuple)
    matched_rejection: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AuthLabVerdictResult:
    """Verdict plus the deterministic rationale behind it.

    This is what a human-facing summary (possibly generated by a model --
    see module docstring) would be built *from*; the model never touches
    ``verdict`` itself, only prose describing ``rationale``.
    """

    verdict: AuthLabVerdict
    rationale: str
    permissive_matches: tuple[ObservationMatch, ...]
    rejection_matches: tuple[ObservationMatch, ...]
    considered_observation_ids: tuple[uuid.UUID, ...]


def evaluate_auth_lab_v1(observations: list[ObservationV1]) -> AuthLabVerdictResult:
    """Deterministically decide the `ghostrange-auth-lab-v1` verdict for a
    set of Observations (typically ``VerificationV1.observation_ids``
    resolved to their records).

    Rule, in priority order (see ASSUMPTION in the module docstring for
    scenario semantics):

    1. If ANY observation matches a permissive/success marker ->
       ``EXPECTED_CONDITION_NOT_OBSERVED``. A single unexpectedly
       permissive response is disqualifying regardless of how many other
       observations show correct rejection -- this mirrors
       ``EVIDENCE.md``'s own worked example, where one successful attack
       observation flips a PASSED verification to FAILED; a security
       property that holds "usually" does not hold.
    2. Else, if ANY observation matches a rejection marker ->
       ``EXPECTED_CONDITION_OBSERVED``.
    3. Else (no observations, or none matched either rule set) ->
       ``INCONCLUSIVE``.

    Pure function: no I/O, no mutation of `observations`, no randomness,
    no clock reads. Same input list (by value) always produces the same
    ``AuthLabVerdictResult.verdict`` -- this is asserted directly in
    ``tests/test_scenario_verification.py::test_verdict_is_deterministic``.
    """
    permissive_matches: list[ObservationMatch] = []
    rejection_matches: list[ObservationMatch] = []

    for obs in observations:
        permissive_hits = tuple(_matches(obs.summary, _PERMISSIVE_MARKERS))
        rejection_hits = tuple(_matches(obs.summary, _REJECTION_MARKERS))
        if permissive_hits:
            permissive_matches.append(ObservationMatch(obs.id, matched_permissive=permissive_hits))
        if rejection_hits:
            rejection_matches.append(ObservationMatch(obs.id, matched_rejection=rejection_hits))

    considered = tuple(o.id for o in observations)

    if permissive_matches:
        rationale = (
            f"{len(permissive_matches)} observation(s) matched a "
            f"permissive/success marker (e.g. {permissive_matches[0].matched_permissive[0]!r} "
            f"on observation {permissive_matches[0].observation_id}) -- an unexpectedly "
            "permissive response was observed, so the expected (rejecting) "
            "condition was NOT observed, regardless of any rejection "
            "evidence also present."
        )
        return AuthLabVerdictResult(
            verdict=AuthLabVerdict.EXPECTED_CONDITION_NOT_OBSERVED,
            rationale=rationale,
            permissive_matches=tuple(permissive_matches),
            rejection_matches=tuple(rejection_matches),
            considered_observation_ids=considered,
        )

    if rejection_matches:
        rationale = (
            f"{len(rejection_matches)} observation(s) matched a rejection "
            f"marker (e.g. {rejection_matches[0].matched_rejection[0]!r} on "
            f"observation {rejection_matches[0].observation_id}) and zero "
            "observations matched a permissive/success marker: the expected "
            "condition (bad credential rejected) was observed."
        )
        return AuthLabVerdictResult(
            verdict=AuthLabVerdict.EXPECTED_CONDITION_OBSERVED,
            rationale=rationale,
            permissive_matches=(),
            rejection_matches=tuple(rejection_matches),
            considered_observation_ids=considered,
        )

    rationale = (
        f"{len(observations)} observation(s) considered; none matched a "
        "permissive/success marker or a rejection marker -- cannot "
        "determine the expected condition from this evidence set."
    )
    return AuthLabVerdictResult(
        verdict=AuthLabVerdict.INCONCLUSIVE,
        rationale=rationale,
        permissive_matches=(),
        rejection_matches=(),
        considered_observation_ids=considered,
    )


def verdict_to_verification_result(verdict: AuthLabVerdict) -> VerificationResult:
    """Map an :class:`AuthLabVerdict` to the contract-level
    ``VerificationResult`` used on ``VerificationV1.result``.

    A Claim under test in this scenario is typically of the shape "the
    remediation correctly rejects the known-bad credential" -- so
    EXPECTED_CONDITION_OBSERVED (rejection happened) means the claim
    PASSED verification, and EXPECTED_CONDITION_NOT_OBSERVED (permissive
    response happened) means it FAILED. This mapping is specific to
    Claims phrased that way; a Claim phrased as its own negation would
    need the mapping inverted at the call site, which is why this helper
    takes a bare verdict rather than assuming a Claim's polarity itself.
    """
    return {
        AuthLabVerdict.EXPECTED_CONDITION_OBSERVED: VerificationResult.PASSED,
        AuthLabVerdict.EXPECTED_CONDITION_NOT_OBSERVED: VerificationResult.FAILED,
        AuthLabVerdict.INCONCLUSIVE: VerificationResult.INCONCLUSIVE,
    }[verdict]


__all__ = [
    "AuthLabVerdict",
    "AuthLabVerdictResult",
    "ObservationMatch",
    "evaluate_auth_lab_v1",
    "verdict_to_verification_result",
]
