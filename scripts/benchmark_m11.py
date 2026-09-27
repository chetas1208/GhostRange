#!/usr/bin/env python3
"""M11 benchmark evaluator — ground truth is separate from gate engine."""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "ghostgate"))

from ghostrange_contracts.adversarial_m8 import (
    AdversarialBudgetV1,
    AdversarialClaimPhase,
    AdversarialVerificationReportV1,
    CounterexampleV1,
    SearchArmKind,
    SearchPolicyId,
    SearchStopReason,
)
from ghostrange_contracts.ghostgate_m11 import ChangeActionKind, ChangeActionV1, PromotionState

from ghostrange_ghostgate.promote import GhostGate, PromotionPrepareInput


def _base_inp(**overrides) -> PromotionPrepareInput:
    base = PromotionPrepareInput(
        experiment_id=uuid.uuid4(),
        remediation_id=uuid.uuid4(),
        source_revision_id=uuid.uuid4(),
        twin_revision_id=uuid.uuid4(),
        evidence_root_digest="bench-evidence",
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def run_scenario(gate: GhostGate, scenario_id: str) -> dict:
    t0 = time.perf_counter()
    if scenario_id == "clean_promotion":
        inp = _base_inp()
    elif scenario_id == "stale_source":
        inp = _base_inp(source_stale=True)
    elif scenario_id == "material_patch_difference":
        inp = _base_inp(
            proposed_actions_override=[
                ChangeActionV1(
                    kind=ChangeActionKind.CONFIG,
                    target_path="other.py",
                    description="diff",
                    remediation_ref="x",
                )
            ]
        )
    elif scenario_id == "rollback_failure":
        inp = _base_inp(rollback_fail=True)
    elif scenario_id == "observability_gap":
        inp = _base_inp(observability_gap=True)
    elif scenario_id == "counterexample_present":
        cid = uuid.uuid4()
        budget = AdversarialBudgetV1(max_attempts=5)
        cx = CounterexampleV1(
            claim_id=cid,
            world_id=uuid.uuid4(),
            search_run_id=uuid.uuid4(),
            action_sequence=[{"m": "GET"}],
            violated_invariant="x",
            claim_contradiction="y",
            discovered_by=SearchArmKind.HEADER_MUTATION,
            search_strategy=SearchPolicyId.UNIFORM_RANDOM,
            search_budget_snapshot=budget,
        )
        adv = AdversarialVerificationReportV1(
            claim_id=cid,
            search_run_id=uuid.uuid4(),
            phase=AdversarialClaimPhase.COUNTEREXAMPLE_FOUND,
            budget=budget,
            search_policy=SearchPolicyId.UNIFORM_RANDOM,
            counterexamples=[cx],
            stop_reason=SearchStopReason.COUNTEREXAMPLE_CONFIRMED,
        )
        inp = _base_inp(adversarial=adv)
    else:
        return {"scenario": scenario_id, "skipped": True}

    res = gate.prepare(inp)
    ms = int((time.perf_counter() - t0) * 1000)
    unsafe_ready = res.candidate.state == PromotionState.READY_FOR_REVIEW and scenario_id != "clean_promotion"
    return {
        "scenario": scenario_id,
        "state": res.candidate.state.value,
        "blockers": res.candidate.readiness.blockers,
        "promotion_analysis_ms": ms,
        "unsafe_ready_for_approval": unsafe_ready,
    }


def main() -> int:
    gt_path = ROOT / "artifacts/benchmarks/m11/ground_truth/scenarios.json"
    gt = json.loads(gt_path.read_text())
    gate = GhostGate()
    results = []
    unsafe_passes = 0
    for sc in gt["scenarios"]:
        sid = sc["id"]
        out = run_scenario(gate, sid)
        if out.get("skipped"):
            continue
        results.append(out)
        if out.get("unsafe_ready_for_approval"):
            unsafe_passes += 1
        exp_state = sc.get("expected_state")
        if exp_state and out["state"] != exp_state:
            out["expected_state_miss"] = exp_state
        exp_block = sc.get("expected_blockers_contains")
        if exp_block and exp_block not in out["blockers"]:
            out["expected_blocker_miss"] = exp_block

    report = {
        "unsafe_promotion_pass_count": unsafe_passes,
        "unsafe_promotion_pass_rate_target": gt["metrics_targets"]["unsafe_promotion_pass_rate"],
        "results": results,
    }
    out_path = ROOT / "artifacts/benchmarks/m11/last_run.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 1 if unsafe_passes > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
