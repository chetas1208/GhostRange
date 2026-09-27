"""Experience eligibility — not all campaign output is training data."""

from __future__ import annotations

from ghostrange_contracts.ghostevolve_m18 import (
    ExperienceClass,
    ExperienceRecordV1,
    LearningEligibility,
)


def classify_experience_eligibility(record: ExperienceRecordV1) -> LearningEligibility:
    if record.safety_outcome not in ("OK", "NEAR_MISS_BLOCKED"):
        return LearningEligibility.REJECTED
    if record.provenance_digest == "" or record.provenance_digest == "FIXTURE":
        return LearningEligibility.QUARANTINED
    if record.experience_class in (ExperienceClass.FAILURE,) and not record.actual_outcome:
        return LearningEligibility.INSUFFICIENT_EVIDENCE
    if "poisoned" in record.context.get("tags", []):
        return LearningEligibility.QUARANTINED
    if record.experience_class == ExperienceClass.AUTHORIZATION_DENIAL:
        return LearningEligibility.ELIGIBLE_WITH_LIMITATIONS
    if record.experience_class == ExperienceClass.SCHEDULING_MISPREDICTION:
        return LearningEligibility.ELIGIBLE
    if record.actual_outcome.get("runtime_seconds") is not None:
        return LearningEligibility.ELIGIBLE
    return LearningEligibility.INSUFFICIENT_EVIDENCE
