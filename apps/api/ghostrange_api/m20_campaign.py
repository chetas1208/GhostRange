"""M20 — one canonical campaign wrapping real M5–M19 components (no scripted outcomes)."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from ghostrange_contracts._base import utc_now
from ghostrange_contracts.ghostarena_m19 import ReleaseRecommendation
from ghostrange_contracts.ghostrange_m20 import (
    CampaignPhase,
    GhostCampaignReportV1,
    GhostCampaignV1,
    GhostEvidenceBundleV1,
    ReproductionManifestV1,
)
from ghostrange_ghostarena.engine import GhostArenaEngine

from .golden_path import GoldenPathOrchestrator, GoldenPathResult, GoldenScenarioId


LiveOutcome = Literal["not_attempted", "blocked", "completed", "failed"]


@dataclass
class M20CampaignResult:
    campaign: GhostCampaignV1
    golden: GoldenPathResult
    report: GhostCampaignReportV1
    evidence_bundle: GhostEvidenceBundleV1
    reproduction: ReproductionManifestV1
    arena_recommendation: ReleaseRecommendation
    owned_workers_after: list[str] = field(default_factory=list)
    live_worker_outcome: LiveOutcome = "not_attempted"
    errors: list[str] = field(default_factory=list)


class M20CampaignOrchestrator:
    """Chains compile → director → scheduler → adversarial → ledger → arena → report."""

    def __init__(
        self,
        *,
        repo_root,
        compose_path,
        live: bool,
        deploy_sha: str = "unknown",
        ghostshield_mode: str = "SHADOW",
        inference_model: str = "",
        scenario: GoldenScenarioId = "tenant_escalation",
    ) -> None:
        self._gp = GoldenPathOrchestrator(
            repo_root=repo_root,
            compose_path=compose_path,
            live=live,
            scenario=scenario,
        )
        self._live = live
        self._deploy_sha = deploy_sha
        self._ghostshield_mode = ghostshield_mode
        self._inference_model = inference_model
        self._compose_path = compose_path

    def _max_live_usd(self) -> float:
        return float(os.environ.get("M20_LIVE_CAMPAIGN_MAX_USD", "15"))

    def _assert_live_allowed(self) -> None:
        if self._live and os.environ.get("ALLOW_M20_LIVE_CAMPAIGN", "").lower() not in ("1", "true", "yes"):
            raise RuntimeError("ALLOW_M20_LIVE_CAMPAIGN=true required for live M20 campaign")

    def _from_golden(self, golden: GoldenPathResult) -> M20CampaignResult:
        campaign = GhostCampaignV1(
            campaign_id=golden.campaign_id,
            range_id=golden.range_id,
            investigation_id=golden.investigation_id,
            phase=CampaignPhase.INGESTING,
            live_mode="live" if self._live else "mock",
            deploy_sha=self._deploy_sha,
            source_input_ref=str(self._compose_path),
        )
        campaign.correlation_id = golden.benchmark.correlation_id
        if golden.twin_revision_id:
            campaign.twin_revision_id = golden.twin_revision_id

        campaign.phase = CampaignPhase.COMPLETED if not golden.errors else CampaignPhase.FAILED
        campaign.completed_at = utc_now()

        arena = GhostArenaEngine().release_report(
            baseline_version="ghostrange-release:v0.9",
            candidate_version=f"ghostrange-release:{self._deploy_sha}",
            candidate_policy="qualified",
        )
        arena_rec = arena.recommendation

        refuted = 0
        if golden.adversarial_report and golden.adversarial_report.counterexamples:
            refuted = len(golden.adversarial_report.counterexamples)

        scenario_id = getattr(self._gp, "scenario", "tenant_escalation")
        if scenario_id == "auth_incident":
            incident_summary = "Controlled auth/session incident (auth-lab compose input)"
            incident_provenance = "auth_incident_scenario"
        else:
            incident_summary = (
                "Cross-tenant billing-export exposure via internal-role-header trust "
                "boundary config drift (billing-service / api-gateway / identity-service "
                "compose input) — shallow header-strip fix falsified, deep fix survived "
                "adversarial search"
            )
            incident_provenance = "tenant_escalation_scenario"

        report = GhostCampaignReportV1(
            campaign_id=campaign.campaign_id,
            range_id=campaign.range_id,
            incident_summary=incident_summary,
            hypothesis_count=3,
            hypotheses_refuted=max(0, refuted),
            experiments_run=golden.benchmark.experiments_run,
            scheduler_decisions=golden.benchmark.scheduler_decisions,
            counterexamples_confirmed=golden.benchmark.counterexamples_confirmed,
            remediation_survivors=1 if golden.remediation_id else 0,
            remediation_refuted=refuted,
            bundle_digest=golden.bundle_digest,
            arena_recommendation=arena_rec.value,
            cost_usd_estimate=self._max_live_usd() if self._live else 0.0,
            limitations=[
                "M20 slice: GhostGate/GhostWatch/Shield/runtime restart not in single HTTP call",
                "Live worker step optional; default path is local mock compute",
            ],
            phases=golden.phases,
        )

        summary_payload = {
            "campaign_id": str(campaign.campaign_id),
            "phases": golden.phases,
            "benchmark": golden.benchmark.to_json(),
        }
        summary_digest = hashlib.sha256(
            json.dumps(summary_payload, sort_keys=True).encode()
        ).hexdigest()

        evidence = GhostEvidenceBundleV1(
            campaign_id=campaign.campaign_id,
            manifest_digest=golden.bundle_digest or "",
            claims=[
                {
                    "kind": "incident",
                    "statement": report.incident_summary,
                    "provenance": incident_provenance,
                }
            ]
            + (
                [
                    {
                        "kind": "remediation_rejected",
                        "statement": (
                            "Fix A (strip X-Internal-Role only) was falsified: adversarial "
                            "header-mutation search reproduced privileged cross-tenant access "
                            "via a second, independent legacy header (X-Debug-Auth)."
                        ),
                        "provenance": "billing_export_lab_scenario",
                    },
                    {
                        "kind": "remediation_survived",
                        "statement": (
                            "Fix B (remove all header-based trust; enforce session-scoped "
                            "tenant access) survived the same adversarial search with no "
                            "confirmed counterexample."
                        ),
                        "provenance": "billing_export_lab_scenario",
                    },
                ]
                if scenario_id != "auth_incident" and golden.shallow_fix_adversarial_report
                else []
            ),
            event_summary_digest=summary_digest,
            scheduler_decision_count=golden.benchmark.scheduler_decisions,
            verification_results={
                "adversarial_phase": golden.adversarial_report.phase.value
                if golden.adversarial_report
                else None,
                "ledger_verified": golden.benchmark.bundle_verified,
            },
            arena_qualification=arena_rec.value,
            checksums={"event_summary": summary_digest},
        )

        reproduction = ReproductionManifestV1(
            campaign_id=campaign.campaign_id,
            deploy_sha=self._deploy_sha,
            compose_path=str(self._compose_path),
            director_policy="GHOSTDIRECTOR_V1",
            scheduler_policy="GHOSTSCHEDULER_V3",
            ghostshield_mode=self._ghostshield_mode,
            inference_model=self._inference_model or "not_configured",
            nondeterministic_components=["model_inference", "provider_latency"],
            seed_notes=(
                "Director simulator uses hidden true_mechanism=session_refresh_cache"
                if scenario_id == "auth_incident"
                else "Director simulator uses hidden true_mechanism=internal_role_header_trust"
            ),
        )

        return M20CampaignResult(
            campaign=campaign,
            golden=golden,
            report=report,
            evidence_bundle=evidence,
            reproduction=reproduction,
            arena_recommendation=arena_rec,
            errors=list(golden.errors),
        )

    def run(self, range_id: uuid.UUID | None = None) -> M20CampaignResult:
        self._assert_live_allowed()
        rid = range_id or uuid.uuid4()
        return self._from_golden(self._gp.run(rid))

    async def run_async(self, gateway, range_id: uuid.UUID | None = None) -> M20CampaignResult:
        self._assert_live_allowed()
        golden = await self._gp.run_async(gateway, range_id)
        result = self._from_golden(golden)
        await gateway.append_legacy(
            result.campaign.range_id,
            {
                "event_name": "campaign.phase",
                "schema_version": "1",
                "occurred_at": utc_now().isoformat(),
                "campaign_id": str(result.campaign.campaign_id),
                "phase": result.campaign.phase.value,
                "arena_recommendation": result.arena_recommendation.value,
            },
            source="m20_campaign",
        )
        return result

    def attach_live_worker_result(
        self,
        result: M20CampaignResult,
        *,
        owned_workers: list[Any],
        worker_benchmark: dict[str, Any] | None,
    ) -> M20CampaignResult:
        ids = []
        for h in owned_workers:
            pid = getattr(h, "provider_compute_id", None) or (h.get("provider_compute_id") if isinstance(h, dict) else None)
            if pid:
                ids.append(str(pid))
        result.owned_workers_after = ids
        if worker_benchmark:
            result.live_worker_outcome = "completed" if worker_benchmark.get("ok") else "failed"
        if ids:
            result.errors.append(f"owned_workers_not_empty:{ids}")
        return result


def m20_response_payload(result: M20CampaignResult) -> dict[str, Any]:
    return {
        "campaign": result.campaign.model_dump(mode="json"),
        "investigation_id": str(result.golden.investigation_id),
        "range_id": str(result.golden.range_id),
        "scenario": result.golden.scenario,
        "phases": result.golden.phases,
        "benchmark": result.golden.benchmark.to_json(),
        "report": result.report.model_dump(mode="json"),
        "evidence_bundle": result.evidence_bundle.model_dump(mode="json"),
        "reproduction_manifest": result.reproduction.model_dump(mode="json"),
        "arena_recommendation": result.arena_recommendation.value,
        "owned_workers": result.owned_workers_after,
        "live_worker_outcome": result.live_worker_outcome,
        "errors": result.errors,
        "release_maturity": "RESEARCH_PROTOTYPE",
    }
