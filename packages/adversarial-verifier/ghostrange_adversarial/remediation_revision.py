from __future__ import annotations

from ghostrange_contracts.adversarial_m8 import CounterexampleV1, RemediationRevisionV1


def propose_revision(
    *,
    parent_remediation_id,
    counterexample: CounterexampleV1,
    parent_label: str = "Fix B",
) -> RemediationRevisionV1:
    idx = parent_label.split(".")[-1] if "." in parent_label else "B"
    if idx.isdigit():
        next_label = f"Fix B.{int(idx) + 1}"
    elif idx == "B":
        next_label = "Fix B.1"
    else:
        next_label = f"{parent_label}.1"
    return RemediationRevisionV1(
        parent_remediation_id=parent_remediation_id,
        child_label=next_label,
        triggered_by_counterexample_id=counterexample.id,
        change_summary=f"Address falsification via {counterexample.violated_invariant}",
    )


__all__ = ["propose_revision"]
