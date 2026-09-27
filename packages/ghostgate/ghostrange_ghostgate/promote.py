"""Prepare promotion from verified experiment context."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ghostrange_contracts.adversarial_m8 import AdversarialVerificationReportV1, SearchStopReason
from ghostrange_contracts.ghostgate_m11 import (
    BundleMode,
    PromotionState,
    ProductionChangeCandidateV1,
    ReadinessDimensionStatus,
    ResidualRiskV1,
    RollbackStatus,
)
from ghostrange_contracts.living_twin_m6 import ClaimValidityStatus, ClaimValidityV1, TwinStalenessV1

from .approval import create_approval_request, policy_for_risk
from .bundle import build_bundle, refresh_candidate_hash
from .equivalence import build_tested_delta, compare_actions
from .gates import GateContext, evaluate_readiness, ready_for_human_review
from .impact import all_affected, compute_blast_radius
from .patch_security import scan_patch
from .patches import auth_lab_remediation_actions, generate_compose_env_patch, generate_terraform_snippet
from .rollback import default_rollback_plan, simulate_rollback_in_range
from .risk import assess_risk
from .strategy import recommend_strategy
from .verification import (
    default_observability,
    default_post_change_plan,
    simulate_verification_plan_in_range,
)


@dataclass
class PromotionPrepareInput:
    experiment_id: uuid.UUID
    remediation_id: uuid.UUID
    source_revision_id: uuid.UUID
    twin_revision_id: uuid.UUID
    evidence_root_digest: str
    claim_ids: list[uuid.UUID] = field(default_factory=list)
    bundle_digest: str | None = None
    adversarial: AdversarialVerificationReportV1 | None = None
    twin_staleness: TwinStalenessV1 | None = None
    claim_validities: list[ClaimValidityV1] = field(default_factory=list)
    fidelity_ok: bool = True
    observability_gap: bool = False
    proposed_actions_override: list | None = None
    rollback_fail: bool = False
    source_stale: bool = False


@dataclass
class PromotionPrepareResult:
    candidate: ProductionChangeCandidateV1
    bundle_path: str | None = None
    events: list[str] = field(default_factory=list)


class GhostGate:
    """Human-controlled promotion boundary."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or Path.cwd()
        self._store: dict[uuid.UUID, ProductionChangeCandidateV1] = {}
        self._idempotency: dict[str, uuid.UUID] = {}

    @staticmethod
    def _idempotency_key(inp: PromotionPrepareInput) -> str:
        payload = {
            "experiment_id": str(inp.experiment_id),
            "source_revision_id": str(inp.source_revision_id),
            "twin_revision_id": str(inp.twin_revision_id),
            "evidence_root_digest": inp.evidence_root_digest,
            "remediation_id": str(inp.remediation_id),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def prepare(self, inp: PromotionPrepareInput) -> PromotionPrepareResult:
        idem = self._idempotency_key(inp)
        existing = self._idempotency.get(idem)
        if existing and existing in self._store:
            return PromotionPrepareResult(
                candidate=self._store[existing],
                events=["promotion.idempotent_replay"],
            )

        events = ["promotion.created", "promotion.equivalence_checked"]
        tested = auth_lab_remediation_actions()
        proposed = inp.proposed_actions_override or list(tested)
        equiv = compare_actions(tested, proposed)
        delta = build_tested_delta(tested, proposed)

        if equiv.overall.value == "MATERIAL_DIFFERENCE":
            events.append("promotion.retest_required")

        staleness = inp.twin_staleness
        if inp.source_stale and staleness is None:
            staleness = TwinStalenessV1(
                twin_revision_id=inp.twin_revision_id,
                config_staleness=0.5,
                overall_semantic=0.2,
            )

        claims = inp.claim_validities
        if not claims and inp.claim_ids:
            claims = [
                ClaimValidityV1(
                    claim_id=cid,
                    status=ClaimValidityStatus.CURRENT,
                    twin_revision_id=inp.twin_revision_id,
                    source_revision_id=inp.source_revision_id,
                )
                for cid in inp.claim_ids
            ]

        rb_status = simulate_rollback_in_range(inject_failure=inp.rollback_fail)
        post_plan = default_post_change_plan()
        post_ok = simulate_verification_plan_in_range(post_plan)
        obs = default_observability(gap=inp.observability_gap)

        ctx = GateContext(
            claim_validities=claims,
            twin_staleness=staleness,
            adversarial=inp.adversarial,
            fidelity_ok=inp.fidelity_ok,
            equivalence=equiv,
            rollback_tested_pass=rb_status == RollbackStatus.TESTED_PASS and post_ok,
            observability_gap=bool(obs.gaps),
            high_uncertainty_blocks=False,
        )
        readiness = evaluate_readiness(ctx)
        events.append("promotion.risk_assessed")

        blast = compute_blast_radius(["auth-service"])
        affected = all_affected(blast)
        risk = assess_risk(proposed, affected)
        strategy = recommend_strategy(risk)
        events.extend(["deployment_strategy.selected", "canary.plan_created", "postchange.plan_created"])

        patch = generate_compose_env_patch(proposed)
        patch += "\n" + generate_terraform_snippet(proposed)
        sec_findings = scan_patch(patch)
        if sec_findings:
            for f in sec_findings:
                events.append(f"promotion.patch_security:{f.code}")
            readiness.blockers.append("UNSAFE_PATCH")
            readiness.approval_readiness = ReadinessDimensionStatus.FAIL

        adv_summary = ""
        if inp.adversarial:
            adv_summary = inp.adversarial.summary_statement or str(inp.adversarial.stop_reason.value)

        residual: list[ResidualRiskV1] = []
        if readiness.adversarial_status == ReadinessDimensionStatus.WARN:
            residual.append(
                ResidualRiskV1(
                    description="Adversarial search budget exhausted without confirmed counterexample.",
                    category="SEARCH_BUDGET",
                    severity="MEDIUM",
                )
            )

        state = PromotionState.ASSESSING
        if material_block(readiness):
            if "SOURCE_DRIFT_RELEVANT" in readiness.blockers:
                state = PromotionState.REQUIRES_REVALIDATION
                events.append("promotion.revalidation_required")
            elif "MATERIAL_TESTED_PRODUCTION_DIFF" in readiness.blockers:
                state = PromotionState.REQUIRES_RETEST
            else:
                state = PromotionState.DRAFT
        elif ready_for_human_review(readiness):
            state = PromotionState.READY_FOR_REVIEW
        else:
            state = PromotionState.DRAFT

        candidate = ProductionChangeCandidateV1(
            remediation_id=inp.remediation_id,
            source_revision_id=inp.source_revision_id,
            twin_revision_id=inp.twin_revision_id,
            experiment_id=inp.experiment_id,
            claim_ids=inp.claim_ids,
            evidence_root_digest=inp.evidence_root_digest,
            affected_components=affected,
            change_actions=proposed,
            tested_delta=delta,
            equivalence=equiv,
            readiness=readiness,
            risk=risk,
            deployment_strategy=strategy,
            rollback_plan=default_rollback_plan(),
            rollback_status=rb_status,
            post_change_verification=post_plan,
            observability=obs,
            residual_risks=residual,
            patch_text=patch,
            state=state,
            adversarial_summary=adv_summary,
            known_limitations=[
                "APPROVED != DEPLOYED",
                "Canary plan validated in GhostRange simulation only when run.",
            ],
        )
        candidate = refresh_candidate_hash(candidate)
        self._store[candidate.id] = candidate
        self._idempotency[idem] = candidate.id

        if state == PromotionState.READY_FOR_REVIEW:
            req = create_approval_request(
                candidate,
                summary="Auth middleware trusted-proxy hardening (Fix B.2)",
            )
            events.append("approval.requested")
            _ = req  # stored in bundle on export

        if rb_status == RollbackStatus.TESTED_PASS:
            events.extend(["rollback.test_passed"])
        elif rb_status == RollbackStatus.TESTED_FAIL:
            events.append("rollback.test_failed")

        return PromotionPrepareResult(candidate=candidate, events=events)

    def get(self, candidate_id: uuid.UUID) -> ProductionChangeCandidateV1 | None:
        return self._store.get(candidate_id)

    def export_bundle(
        self,
        candidate_id: uuid.UUID,
        *,
        experiment_root_digest: str = "",
    ) -> str:
        cand = self._store.get(candidate_id)
        if not cand:
            raise KeyError(candidate_id)
        bundle = build_bundle(
            cand,
            mode=BundleMode.CI_ARTIFACT,
            experiment_root_digest=experiment_root_digest or cand.evidence_root_digest,
        )
        events = ["promotion.bundle_created"]
        _ = events
        return bundle.model_dump_json(indent=2)


def material_block(readiness) -> bool:
    return bool(readiness.blockers)
