"""The concrete mechanism against "arbitrary-target injection via free-form
model output" (THREAT_MODEL.md T1/T2/T10, EXECUTION_POLICY.md §3.1).

The rule this module enforces in code, not just in prose: model output is
NEVER converted directly into a ``TargetRef``. A DAG node, at compile time
(before the agent reasons about that node at all), pre-declares a small set
of opaque aliases for the targets it's allowed to touch (e.g.
``"target-0"``, or a stable per-asset alias execution-graph chose). The
agent's tool-call output may only select one of those alias strings — it
can never supply ``host_or_ip`` text of its own invention. This function is
the ONLY sanctioned path by which a string that originated in model output
becomes a real ``TargetRef``: it looks the alias up in policy-check's own
registry (populated only at range-provisioning time from real IaC output,
never from anything an agent said) and raises if the alias isn't
recognized — it never falls back to constructing a ``TargetRef`` from
whatever text was given.

Downstream, ``authorize()`` re-checks the resolved ``TargetRef`` against
the same registry's canonical target set anyway (EXECUTION_POLICY.md §3.2
step 2) — this module is the layer *before* that, closing off the "the
model just typed a raw IP into a tool call" failure mode at the point
where free text would otherwise enter the system, and is Pydantic-adjacent
defense in depth for the ``target_refs`` field ``ExecutionRequestV1``
already constrains (policy.py).
"""

from __future__ import annotations

from ghostrange_contracts._base import Id
from ghostrange_contracts.policy import TargetRef

from .registry import PolicyRegistry, UnknownRangeError


class UnknownTargetAliasError(Exception):
    """Raised when model output names a target alias that was not
    pre-declared for this range at DAG-compile/provisioning time. This is
    the expected outcome for "the model tried to reference a target that
    was never offered to it" — including a raw IP/hostname string, since
    those are never valid aliases.
    """


def resolve_target(range_id: Id, target_alias: str, registry: PolicyRegistry) -> TargetRef:
    """Convert a model-selected, pre-declared target alias into the real
    ``TargetRef`` it stands for. Raises on anything not in the registry's
    alias map for this range — including a well-formed-looking IP or
    hostname the model invented, since a raw string is never itself a
    valid alias regardless of how plausible it looks.
    """
    try:
        aliases = registry.get_target_aliases(range_id)
    except UnknownRangeError:
        raise UnknownTargetAliasError(
            f"range {range_id} has no registered target aliases (unknown or torn-down range)"
        ) from None
    try:
        return aliases[target_alias]
    except KeyError:
        raise UnknownTargetAliasError(
            f"{target_alias!r} is not a pre-declared target alias for range {range_id}; "
            "model output must select among pre-enumerated aliases, never supply "
            "a target string directly"
        ) from None


__all__ = ["UnknownTargetAliasError", "resolve_target"]
