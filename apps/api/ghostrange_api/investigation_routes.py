"""Investigation intake — GitHub repo + incident description as the primary
input for starting a GhostRange investigation.

Product direction (see docs/architecture/PRODUCT.md): a GitHub repository
URL + a plain-English incident description should be enough to start an
investigation. This router is the first real slice of that: it accepts the
minimum input contract, runs the heuristic repo scan
(``ghostrange_range_compiler.intake``), and returns a
``DerivedSystemModelV1`` plus the narration counts the product wants shown
in the first ~20 seconds ("N files relevant... N services identified...").

Explicitly out of scope for this pass (see module docstrings in
``ghostrange_range_compiler.intake`` and
``ghostrange_contracts.derived_system_model``):
- Private repositories / GitHub App or OAuth auth.
- Full static analysis / AST parsing (this is heuristic file/pattern
  matching only).
- Feeding the derived model into RangeSpec compilation or provisioning —
  that integration is a separate follow-up task.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from ghostrange_contracts.investigation_intake import InvestigationIntakeV1
from ghostrange_range_compiler.intake import RepositoryAcquisitionError, analyze_repository

router = APIRouter(prefix="/v1/investigations", tags=["investigations"])


def _narration_lines(model) -> list[str]:
    s = model.summary
    return [
        "Repository acquired.",
        f"{s.files_relevant} files relevant of {s.files_scanned} scanned.",
        f"{s.services_identified} services identified.",
        f"{s.data_stores_identified} data stores identified.",
        f"{s.external_interfaces_identified} external interfaces identified.",
    ]


@router.post("/intake")
def intake(request: InvestigationIntakeV1) -> dict:
    """Analyze ``request.system.repository_url``@``branch`` and return a
    candidate system model. Synchronous ``def`` (not ``async def``) so
    FastAPI runs the blocking ``git clone`` + filesystem walk in its
    threadpool rather than on the event loop."""
    try:
        model = analyze_repository(request.system.repository_url, request.system.branch)
    except RepositoryAcquisitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "case_id": request.case_id,
        "incident": request.incident.model_dump(mode="json"),
        "derived_system_model": model.model_dump(mode="json"),
        "narration": _narration_lines(model),
    }


__all__ = ["router"]
