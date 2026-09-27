from __future__ import annotations

import hashlib
import json

from ghostrange_contracts.ghostdirector_m9 import ExperimentProposalV1


def proposal_fingerprint(proposal: ExperimentProposalV1) -> str:
    if proposal.fingerprint:
        return proposal.fingerprint
    body = {
        "objective": proposal.objective,
        "operators": [o.model_dump(mode="json") for o in proposal.operators],
        "hypotheses": [str(h) for h in proposal.hypotheses_tested],
    }
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def dedupe_proposals(proposals: list[ExperimentProposalV1]) -> list[ExperimentProposalV1]:
    seen: set[str] = set()
    out: list[ExperimentProposalV1] = []
    for p in proposals:
        fp = proposal_fingerprint(p)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(p.model_copy(update={"fingerprint": fp}))
    return out


__all__ = ["proposal_fingerprint", "dedupe_proposals"]
