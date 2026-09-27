"""Secret sanitization — references only, synthetic replacements."""

from __future__ import annotations

from ghostrange_contracts.source_model import SourceModelV1
from ghostrange_contracts.system_graph import NormalizedSystemGraphV1
from ghostrange_contracts.twin_compiler import TwinSecretSubstitutionV1


def sanitize_secrets(
    source: SourceModelV1,
    graph: NormalizedSystemGraphV1,
) -> tuple[NormalizedSystemGraphV1, list[TwinSecretSubstitutionV1], list[str]]:
    """Return graph (unchanged structurally), substitution records, audit lines."""
    subs: list[TwinSecretSubstitutionV1] = []
    decisions: list[str] = []
    for ref in source.secrets_references:
        twin_ref = f"ghostrange/ephemeral/{ref.replace('.', '/')}"
        subs.append(
            TwinSecretSubstitutionV1(
                original_reference=ref,
                replacement_type="TWIN_EPHEMERAL",
                twin_secret_ref=twin_ref,
            )
        )
        decisions.append(f"secret reference {ref} → {twin_ref}")
    return graph, subs, decisions


__all__ = ["sanitize_secrets"]
