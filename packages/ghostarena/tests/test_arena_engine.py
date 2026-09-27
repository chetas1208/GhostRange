import tempfile
from pathlib import Path

import pytest

from ghostrange_contracts.ghostarena_m19 import ReleaseRecommendation, RunQualification
from ghostrange_ghostarena.engine import GhostArenaEngine
from ghostrange_ghostarena.hidden_store import ArenaHiddenStore


@pytest.fixture
def engine(tmp_path: Path) -> GhostArenaEngine:
    store = ArenaHiddenStore(root=tmp_path / "private")
    return GhostArenaEngine(store=store)


def test_premature_stop_trap_rejects_fast_candidate(engine: GhostArenaEngine):
    run = engine.run_paired(
        "premature-stop-trap-v1",
        baseline_version="stopping-policy:v5",
        candidate_version="stopping-policy:v6",
        candidate_policy="fast_premature",
    )
    assert run.outcome.passed is False
    assert run.qualification == RunQualification.FAILURE
    assert run.failure_localization is not None
    assert run.failure_localization.failure_type.value == "PREMATURE_STOP"


def test_release_report_not_qualified_demo(engine: GhostArenaEngine):
    report = engine.release_report(
        baseline_version="stopping-policy:v5",
        candidate_version="stopping-policy:v6",
        candidate_policy="fast_premature",
    )
    assert report.recommendation == ReleaseRecommendation.NOT_QUALIFIED
    assert report.hidden_generalization_regression or report.sanitized_diagnostics
    assert report.cost_delta_pct == -21.0


def test_release_report_qualified(engine: GhostArenaEngine):
    report = engine.release_report(
        baseline_version="runtime-estimator:v6",
        candidate_version="runtime-estimator:v7",
        candidate_policy="qualified",
    )
    assert report.recommendation == ReleaseRecommendation.QUALIFIED
    assert not report.safety_regression


def test_overfit_visible_rejected(engine: GhostArenaEngine):
    report = engine.release_report(
        baseline_version="policy:v1",
        candidate_version="policy:v2",
        candidate_policy="overfit_visible",
    )
    assert report.recommendation == ReleaseRecommendation.NOT_QUALIFIED
