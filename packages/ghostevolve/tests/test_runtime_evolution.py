from uuid import uuid4

from ghostrange_contracts.ghostevolve_m18 import (
    ExperienceClass,
    ExperienceRecordV1,
    LearningSurface,
)
from datetime import timedelta

from ghostrange_contracts._base import utc_now

from ghostrange_ghostevolve import (
    GhostExperienceStore,
    evaluate_runtime_candidate,
    temporal_train_test_split,
    classify_experience_eligibility,
)
from ghostrange_contracts.ghostevolve_m18 import LearningEligibility


_seq = 0


def _rec(task_class: str, runtime: float, *, tag: str = "verified") -> ExperienceRecordV1:
    global _seq
    _seq += 1
    return ExperienceRecordV1(
        campaign_id=uuid4(),
        experience_class=ExperienceClass.SCHEDULING_MISPREDICTION,
        context={"task_class": task_class, "tags": [tag]},
        predictions={"prior_seconds": 30.0},
        actual_outcome={"runtime_seconds": runtime},
        provenance_digest="sha256:demo",
        recorded_at=utc_now() + timedelta(seconds=_seq),
    )


def test_poisoned_experience_quarantined():
    rec = _rec("cpu_benchmark", 40.0, tag="poisoned")
    assert classify_experience_eligibility(rec) == LearningEligibility.QUARANTINED


def test_temporal_split_no_future_in_train():
    records = [_rec("cpu_benchmark", 30.0 + i) for i in range(10)]
    train, test = temporal_train_test_split(records, train_fraction=0.7)
    assert len(train) == 7
    assert len(test) == 3
    assert max(r.recorded_at for r in train) <= min(r.recorded_at for r in test)


def test_runtime_candidate_beats_champion_on_future_holdout():
    store = GhostExperienceStore()
    records = []
    for i in range(24):
        r = _rec("cpu_benchmark", 55.0)
        records.append(store.append(r))
    train, future = temporal_train_test_split(records, train_fraction=0.75)
    old_holdout = [records[0], records[1], records[2]]
    candidate, result = evaluate_runtime_candidate(train, future, old_holdout)
    assert result.mae_candidate <= result.mae_champion
    assert result.passed
    assert candidate.version_label.startswith("runtime-estimator")


def test_bad_challenger_worse_on_old_bursty_workload():
    from ghostrange_ghostevolve.evaluation import _mae
    from ghostrange_ghostevolve.runtime_estimator import M15RuntimeEstimatorChampion, RuntimeEstimatorCandidate

    old = [_rec("bursty_cpu", 120.0) for _ in range(5)]
    champ = M15RuntimeEstimatorChampion()
    bad = RuntimeEstimatorCandidate(version_label="warm-retention:v8-bad")
    bad.class_means = {"bursty_cpu": 200.0}
    assert _mae(old, bad) > _mae(old, champ)
