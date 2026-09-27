"""Load GhostWatch policy — thresholds are not LLM-improvised."""

from __future__ import annotations

from pathlib import Path

import yaml

from ghostrange_contracts.ghostwatch_m12 import (
    ConformanceDimension,
    DeploymentAuthorityMode,
    GhostWatchPolicyV1,
)


def load_policy(path: Path | None = None) -> GhostWatchPolicyV1:
    path = path or Path("config/ghostwatch-policy.yaml")
    if not path.is_file():
        return GhostWatchPolicyV1()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    auth = data.get("default_authority", "OBSERVE_ONLY")
    dims = data.get("required_conformance_dimensions", ["ARTIFACT", "CONFIGURATION"])
    return GhostWatchPolicyV1(
        version=str(data.get("version", "ghostwatch-v1")),
        default_authority=DeploymentAuthorityMode(auth),
        required_conformance_dimensions=[ConformanceDimension(d) for d in dims],
        missing_data_policy=str(data.get("missing_data_policy", "HOLD")),
        debounce_consecutive_failures=int(data.get("debounce_consecutive_failures", 2)),
        control_fail_closed=bool(data.get("control_fail_closed", True)),
    )
