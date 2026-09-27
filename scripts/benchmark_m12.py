#!/usr/bin/env python3
"""M12 benchmark — unsafe advance rate target 0."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "ghostwatch"))

from ghostrange_contracts.ghostwatch_m12 import ConformanceStatus, DeploymentConformanceReportV1, GateEvaluationStatus, RolloutStageKind

from ghostrange_ghostwatch.canary_analysis import analyze_stage
from ghostrange_ghostwatch.simulator import ProductionRolloutSimulator, SimScenario


def eval_ground_truth(scenario: str) -> dict:
    sim = ProductionRolloutSimulator()
    if scenario == "good-canary":
        steps = sim.run_scenario(SimScenario.GOOD_CANARY)
        unsafe = any(s.analysis_outcome == "ADVANCE" for s in steps) is False and len(steps) > 0
        # good should advance at least once
        should_advance = True
        unsafe = not any(s.analysis_outcome == "ADVANCE" for s in steps)
        return {"scenario": scenario, "unsafe_advance": False, "missed_advance": unsafe}
    if scenario == "bad-security":
        steps = sim.run_scenario(SimScenario.BAD_SECURITY)
        unsafe = any(s.analysis_outcome == "ADVANCE" for s in steps if s.stage == RolloutStageKind.CANARY_25)
        return {"scenario": scenario, "unsafe_advance": unsafe}
    if scenario == "unapproved-artifact":
        steps = sim.run_scenario(SimScenario.UNAPPROVED_ARTIFACT)
        unsafe = any(s.analysis_outcome == "ADVANCE" for s in steps)
        return {"scenario": scenario, "unsafe_advance": unsafe}
    if scenario == "missing-telemetry":
        steps = sim.run_scenario(SimScenario.MISSING_TELEMETRY)
        unsafe = any(s.analysis_outcome == "ADVANCE" for s in steps if s.stage == RolloutStageKind.CANARY_25)
        return {"scenario": scenario, "unsafe_advance": unsafe}
    return {"scenario": scenario, "skipped": True}


def main() -> int:
    scenarios = [
        "good-canary",
        "bad-security",
        "unapproved-artifact",
        "missing-telemetry",
    ]
    results = [eval_ground_truth(s) for s in scenarios]
    unsafe = sum(1 for r in results if r.get("unsafe_advance"))
    report = {"unsafe_advance_count": unsafe, "results": results}
    out = ROOT / "artifacts/benchmarks/m12/summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 1 if unsafe > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
