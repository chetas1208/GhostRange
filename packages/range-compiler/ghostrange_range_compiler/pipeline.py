"""RangeCompiler orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from ghostrange_contracts.fidelity_m5 import InvestigationObjectiveV1
from ghostrange_contracts.ghost_ir import GhostIRV1
from ghostrange_contracts.range_v2 import RangeSpecV2
from ghostrange_contracts.source_model import SourceModelV1, SourceType
from ghostrange_contracts.system_graph import NormalizedSystemGraphV1
from ghostrange_contracts.twin_compiler import (
    CompilationManifestV1,
    CompilerState,
    PlacementPlanV1,
    SanitizationPolicyV1,
    TwinBlueprintV1,
)
from ghostrange_contracts.fidelity_m5 import FidelityReportV1

from .compile.blueprint import build_blueprint, graph_to_ir
from .compile.placement import plan_placement
from .compile.to_rangespec import blueprint_to_rangespec_v2
from .fidelity.gates import build_compose_scores, evaluate_gate
from .fidelity.profile import profile_for_objective
from .importers.compose import compose_to_graph, parse_compose_file
from .importers.k8s import k8s_to_graph, parse_k8s_file
from .importers.terraform import parse_terraform_file, terraform_to_graph
from .sanitize.secrets import sanitize_secrets


@dataclass
class CompilationResult:
    state: CompilerState
    source: SourceModelV1
    graph: NormalizedSystemGraphV1
    ir: GhostIRV1
    blueprint: TwinBlueprintV1
    placement: PlacementPlanV1
    manifest: CompilationManifestV1
    range_spec: RangeSpecV2
    fidelity_report: FidelityReportV1
    errors: list[str] = field(default_factory=list)


class RangeCompiler:
    def __init__(self, *, policy: SanitizationPolicyV1 | None = None) -> None:
        self.policy = policy or SanitizationPolicyV1()

    def compile_compose(
        self,
        compose_path: Path,
        *,
        owner: str = "authorized-operator@ghostrange.local",
        range_name: str = "compiled-twin",
        objective: InvestigationObjectiveV1 | None = None,
    ) -> CompilationResult:
        objective = objective or InvestigationObjectiveV1(
            title="Auth remediation validation",
            description="Compile twin for authentication investigation",
            investigation_kind="auth_remediation",
        )
        errors: list[str] = []

        source = parse_compose_file(compose_path)
        high_risk_plaintext = (
            w
            for w in source.warnings
            if w.code == "PLAINTEXT_SECRET_ENV"
            and any(k in w.message for k in ("AUTH_SECRET", "API_KEY", "TOKEN", "PRIVATE_KEY"))
        )
        if any(high_risk_plaintext) and self.policy.reject_plaintext_secrets:
            errors.append("PRODUCTION_SECRET_REJECTED")

        graph = compose_to_graph(source, compose_path)
        graph, subs, san_decisions = sanitize_secrets(source, graph)
        profile = profile_for_objective(objective)
        ir = graph_to_ir(graph)
        blueprint = build_blueprint(ir, graph, profile.id, subs)
        placement = plan_placement(blueprint.id, graph, profile)
        manifest = CompilationManifestV1(
            source_hashes=[f.content_hash for f in source.files],
            parser_versions={source.parser_id: source.parser_version},
            warnings=[w.message for w in source.warnings],
            sanitization_decisions=san_decisions,
            substitutions=[s.original_reference for s in subs],
            placement_decisions=[placement.explanation or ""],
            fidelity_profile=profile,
            blueprint_hash=blueprint.blueprint_hash,
        )
        range_spec = blueprint_to_rangespec_v2(blueprint, placement, manifest, owner=owner, name=range_name)
        scores = build_compose_scores()
        fidelity = evaluate_gate(profile, scores, world_id=uuid4())

        state = CompilerState.VALIDATING_PLAN if not errors else CompilerState.FAILED
        if errors and self.policy.reject_plaintext_secrets:
            fidelity = fidelity.model_copy(update={"valid_for_investigation": False, "failure_reason": "; ".join(errors)})

        return CompilationResult(
            state=state,
            source=source,
            graph=graph,
            ir=ir,
            blueprint=blueprint,
            placement=placement,
            manifest=manifest,
            range_spec=range_spec,
            fidelity_report=fidelity,
            errors=errors,
        )

    def compile_path(self, path: Path, **kwargs) -> CompilationResult:
        suffix = path.suffix.lower()
        if path.name.endswith(".yaml") or path.name.endswith(".yml"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "services:" in text and "kind:" not in text.split("\n", 5)[0]:
                return self.compile_compose(path, **kwargs)
            source = parse_k8s_file(path)
            graph = k8s_to_graph(source, path)
            return self._finish_generic(source, graph, path, **kwargs)
        if suffix == ".tf":
            source = parse_terraform_file(path)
            graph = terraform_to_graph(source)
            return self._finish_generic(source, graph, path, **kwargs)
        raise ValueError(f"Unsupported source path: {path}")

    def _finish_generic(self, source: SourceModelV1, graph: NormalizedSystemGraphV1, path: Path, **kwargs) -> CompilationResult:
        objective = kwargs.get("objective") or InvestigationObjectiveV1(
            title="Generic compile",
            description=str(path),
            investigation_kind="generic",
        )
        graph, subs, san_decisions = sanitize_secrets(source, graph)
        profile = profile_for_objective(objective)
        ir = graph_to_ir(graph)
        blueprint = build_blueprint(ir, graph, profile.id, subs)
        placement = plan_placement(blueprint.id, graph, profile)
        manifest = CompilationManifestV1(
            source_hashes=[f.content_hash for f in source.files],
            parser_versions={source.parser_id: source.parser_version},
            sanitization_decisions=san_decisions,
            blueprint_hash=blueprint.blueprint_hash,
            fidelity_profile=profile,
        )
        range_spec = blueprint_to_rangespec_v2(
            blueprint,
            placement,
            manifest,
            owner=kwargs.get("owner", "authorized-operator@ghostrange.local"),
            name=kwargs.get("range_name", "compiled-twin"),
        )
        scores = build_compose_scores(topology=0.9 if source.source_type == SourceType.TERRAFORM else 1.0)
        fidelity = evaluate_gate(profile, scores, world_id=uuid4())
        return CompilationResult(
            state=CompilerState.VALIDATING_PLAN,
            source=source,
            graph=graph,
            ir=ir,
            blueprint=blueprint,
            placement=placement,
            manifest=manifest,
            range_spec=range_spec,
            fidelity_report=fidelity,
        )


__all__ = ["RangeCompiler", "CompilationResult"]
