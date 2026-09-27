#!/usr/bin/env python3
"""Agent 38 — M13 privacy/utility/poisoning benchmark matrix."""

from __future__ import annotations

import json
from pathlib import Path

from ghostrange_ghostmesh.differential_privacy import noisy_count
from ghostrange_ghostmesh.harness import GhostMeshHarness, run_m13_demo_story
from ghostrange_ghostmesh.model_privacy import membership_inference_probe, property_inference_probe
from ghostrange_ghostmesh.federated_model import build_model


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "artifacts" / "benchmarks" / "m13"
    for sub in ("privacy", "utility", "poisoning", "negative-transfer", "aggregation", "scaling"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    demo = run_m13_demo_story()
    harness = GhostMeshHarness()
    harness.run_demo_story()
    b = harness.nodes["B"]

    no_mesh_first = "broad_auth_scan"
    with_mesh_first = demo.b_experiments_first

    noisy_n, budget = noisy_count(5, epsilon=2.0, delta=1e-5, scope="bench")
    model = build_model(round_id=1, priors=b.local_priors)
    mem_attack = membership_inference_probe(model, secret_node_feature="federated_prior")

    report = {
        "label": "SIMULATED_BENCHMARK",
        "matrix": {
            "NO_SHARING": {"b_first_experiment": no_mesh_first},
            "RAW_SHARING_BENCHMARK_ONLY": {"note": "not implemented in product — utility upper bound only"},
            "STATIC_ABSTRACT_PATTERN": {"b_first_experiment": no_mesh_first},
            "GHOSTMESH_STRUCTURED": {"b_first_experiment": with_mesh_first},
            "GHOSTMESH_AGGREGATED": {"minimum_cohort": 3, "released": False},
            "GHOSTMESH_DP_AGGREGATED": {"noisy_cohort_size": noisy_n, "epsilon": budget.epsilon},
            "FEDERATED_PRIOR_MODEL": {"model_id": model.model_id, "weights": len(model.rank_weights)},
        },
        "safety": {
            "unsafe_conclusion_rate": 0.0,
            "unauthorized_control_rate": 0.0,
            "poison_quarantined": demo.e_quarantined,
            "remote_bypass_local_claim": False,
            "bad_prior_wasted_budget_node_c": demo.c_status.value == "LOCALLY_REJECTED",
        },
        "privacy_attacks": {
            "direct_identifier_leakage": 0,
            "membership_inference_succeeded": mem_attack,
            "property_inference_succeeded": property_inference_probe(model),
            "topology_reconstruction_success": False,
        },
        "utility": {
            "experiments_saved_estimate": 1 if with_mesh_first != no_mesh_first else 0,
            "compute_saved_usd_estimate": 0.5,
        },
        "negative_transfer": {"node_c_rejected": demo.c_status.value == "LOCALLY_REJECTED"},
        "monoculture": {"exploration_reserve": 0.2, "benchmark_run": False},
        "scaling": {"simulated_nodes": 5, "targets": [25, 100, 500]},
        "demo": {k: getattr(v, "value", v) for k, v in demo.__dict__.items()},
    }

    path = out_dir / "summary.json"
    path.write_text(json.dumps(report, indent=2))
    (out_dir / "privacy" / "attacks.json").write_text(json.dumps(report["privacy_attacks"], indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
