"""Tested twin change vs proposed production change."""

from __future__ import annotations

import hashlib

from ghostrange_contracts.ghostgate_m11 import (
    ChangeActionV1,
    ChangeEquivalenceReportV1,
    EquivalenceDimension,
    EquivalenceStatus,
    TestedProductionDeltaV1,
)


def _actions_digest(actions: list[ChangeActionV1]) -> str:
    payload = [a.model_dump(mode="json") for a in actions]
    import json

    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_tested_delta(
    tested: list[ChangeActionV1],
    proposed: list[ChangeActionV1],
) -> TestedProductionDeltaV1:
    return TestedProductionDeltaV1(
        tested_actions=tested,
        proposed_actions=proposed,
        tested_patch_digest=_actions_digest(tested),
        proposed_patch_digest=_actions_digest(proposed),
    )


def compare_actions(
    tested: list[ChangeActionV1],
    proposed: list[ChangeActionV1],
) -> ChangeEquivalenceReportV1:
    td = _actions_digest(tested)
    pd = _actions_digest(proposed)
    dims: dict[str, EquivalenceStatus] = {}
    notes: list[str] = []

    if td == pd:
        for dim in EquivalenceDimension:
            dims[dim.value] = EquivalenceStatus.EXACT
        overall = EquivalenceStatus.EXACT
    else:
        tested_map = {a.target_path: a for a in tested}
        proposed_map = {a.target_path: a for a in proposed}
        all_paths = set(tested_map) | set(proposed_map)
        missing = [p for p in all_paths if p not in tested_map or p not in proposed_map]
        mismatched = [
            p
            for p in all_paths
            if p in tested_map and p in proposed_map and tested_map[p] != proposed_map[p]
        ]
        if missing or mismatched or len(tested) != len(proposed):
            overall = EquivalenceStatus.MATERIAL_DIFFERENCE
            notes.append("Proposed production actions differ from tested remediation actions.")
            for dim in EquivalenceDimension:
                dims[dim.value] = (
                    EquivalenceStatus.MATERIAL_DIFFERENCE
                    if dim == EquivalenceDimension.CONFIGURATION
                    else EquivalenceStatus.NOT_COMPARABLE
                )
        else:
            for dim in EquivalenceDimension:
                dims[dim.value] = EquivalenceStatus.FUNCTIONALLY_EQUIVALENT
            overall = EquivalenceStatus.FUNCTIONALLY_EQUIVALENT

    return ChangeEquivalenceReportV1(dimensions=dims, overall=overall, notes=notes)


def material_difference(report: ChangeEquivalenceReportV1) -> bool:
    return report.overall == EquivalenceStatus.MATERIAL_DIFFERENCE
