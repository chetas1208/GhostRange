"""Pluggable per-scenario mechanics for :class:`GhostDirectorSimulator`.

The acquisition/portfolio/validation machinery in ``generate.py``, ``portfolio.py`` and
``validate.py`` is genuinely scenario-agnostic. What *was* scenario-specific — which probe
(``test_id``) discriminates which hypotheses, what a probe result implies about hypothesis
status, and how a "surprise" observation mints a new (initially hidden) hypothesis — used to
be hard-imported from ``scenarios/auth_incident.py`` directly inside ``director.py`` and
``generate.py``. That made it impossible to point the simulator at a second incident without
copy-pasting the whole director.

``ScenarioMechanics`` is the seam: a small bundle of callables + probe specs that a scenario
module builds once (see ``scenarios/auth_incident.py`` for the original, unchanged scenario,
and ``scenarios/tenant_escalation.py`` for the new golden-path scenario). ``default_mechanics()``
reproduces the original auth-incident behavior byte-for-byte, so every existing caller that
constructs ``GhostDirectorSimulator()`` / calls ``generate_candidates(knowledge)`` without an
explicit ``mechanics=`` keeps working exactly as before.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ghostrange_contracts.ghostdirector_m9 import (
    BeliefLevel,
    ExperimentOperatorKind,
    InvestigationHypothesisStatus,
    InvestigationHypothesisV1,
    InvestigationKnowledgeStateV1,
    SurpriseObservationV1,
)


@dataclass(frozen=True)
class ProbeSpec:
    """One probe experiment a scenario wants ``generate_candidates`` to be able to propose.

    ``objective`` may contain ``{h1}``/``{h2}`` (discriminator probe) or ``{hid}``
    (per-hypothesis probe) placeholders; plain text is left untouched by ``.format()``.
    ``matches`` is only consulted for the hidden probe, to decide (a) whether it should be
    proposed at all this round and (b) which hypotheses it targets.
    """

    test_id: str
    operator_kind: ExperimentOperatorKind
    objective: str
    target_asset_id: str = "asset/gw01"
    cost_usd: float = 0.8
    runtime_sec: int = 45
    discriminating_power: BeliefLevel = BeliefLevel.MEDIUM
    discriminate_observation_key: str = "middleware_first"
    matches: Callable[[InvestigationHypothesisV1], bool] = field(default=lambda h: True)


@dataclass(frozen=True)
class ScenarioMechanics:
    """Everything about a scenario's *content* the generic director loop calls back into."""

    simulate_observation: Callable[..., dict]
    update_knowledge: Callable[[InvestigationKnowledgeStateV1, object, dict], None]
    detect_surprise: Callable[..., "SurpriseObservationV1 | None"]
    propose_hypothesis_from_surprise: Callable[
        [InvestigationKnowledgeStateV1, "SurpriseObservationV1"], InvestigationHypothesisV1
    ]
    discriminate_probe: ProbeSpec
    per_hypothesis_probe: ProbeSpec
    hidden_probe: ProbeSpec | None = None
    surprise_followup_question: str = "Session refresh interaction?"


def _default_update_knowledge(knowledge: InvestigationKnowledgeStateV1, prop, result: dict) -> None:
    """Original ``GhostDirectorSimulator._update_knowledge`` body — auth-incident scenario."""
    if result.get("ordering_correct"):
        for h in knowledge.hypothesis_graph.hypotheses:
            if "middleware ordering" in h.statement.lower():
                h.status = InvestigationHypothesisStatus.REFUTED
    if result.get("route_ok"):
        for h in knowledge.hypothesis_graph.hypotheses:
            if "gateway route" in h.statement.lower():
                h.status = InvestigationHypothesisStatus.WEAKENED
    if result.get("session_refresh_bug"):
        for h in knowledge.hypothesis_graph.hypotheses:
            if "session refresh" in h.statement.lower():
                h.status = InvestigationHypothesisStatus.SUPPORTED
    if result.get("ordering_correct") and result.get("route_ok"):
        for h in knowledge.hypothesis_graph.hypotheses:
            if "identity cache" in h.statement.lower() and h.status == InvestigationHypothesisStatus.ACTIVE:
                h.status = InvestigationHypothesisStatus.UNRESOLVED


def default_mechanics() -> ScenarioMechanics:
    """Original M9/M10 auth-incident scenario, unchanged. This is the fallback every existing
    caller gets when it does not pass ``mechanics=`` explicitly."""
    from .scenarios.auth_incident import simulate_observation
    from .surprise import detect_surprise, propose_hypothesis_from_surprise

    return ScenarioMechanics(
        simulate_observation=simulate_observation,
        update_knowledge=_default_update_knowledge,
        detect_surprise=detect_surprise,
        propose_hypothesis_from_surprise=propose_hypothesis_from_surprise,
        discriminate_probe=ProbeSpec(
            test_id="middleware_order_probe",
            operator_kind=ExperimentOperatorKind.COLLECT_OBSERVATION,
            objective="Discriminate {h1} vs {h2}",
            target_asset_id="asset/gw01",
            cost_usd=0.5,
            runtime_sec=30,
            discriminating_power=BeliefLevel.HIGH,
            discriminate_observation_key="middleware_first",
        ),
        per_hypothesis_probe=ProbeSpec(
            test_id="gateway_route_probe",
            operator_kind=ExperimentOperatorKind.COLLECT_OBSERVATION,
            objective="Gateway routing probe for hypothesis {hid}",
            target_asset_id="asset/gw01",
            cost_usd=1.0,
            runtime_sec=60,
            discriminating_power=BeliefLevel.MEDIUM,
        ),
        hidden_probe=ProbeSpec(
            test_id="session_refresh_probe",
            operator_kind=ExperimentOperatorKind.CHANGE_SYNTHETIC_IDENTITY_STATE,
            objective="Session refresh + cache interaction probe",
            target_asset_id="asset/gw01",
            cost_usd=0.8,
            runtime_sec=45,
            discriminating_power=BeliefLevel.HIGH,
            matches=lambda h: "session refresh" in h.statement.lower(),
        ),
    )


__all__ = ["ProbeSpec", "ScenarioMechanics", "default_mechanics"]
