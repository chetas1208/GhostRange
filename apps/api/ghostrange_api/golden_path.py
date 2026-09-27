"""M10 canonical golden path — chains M5–M9 without new subsystems.

Default scenario is ``tenant_escalation`` (cross-tenant billing-export exposure via
config-drift header trust — see ``ghostrange_director.scenarios.tenant_escalation`` and
``ghostrange_adversarial.scenarios.billing_export_lab``): a stronger replacement for the
original ``auth_incident`` scenario (3 hypotheses that were all auth/cache flavors of one
mechanism, single remediation candidate). The original scenario is kept fully intact and
independently tested (``packages/ghostdirector/tests/test_director.py``,
``packages/adversarial-verifier/tests/test_adversarial.py``) — pass
``scenario="auth_incident"`` to run it here too.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ghostrange_contracts._base import utc_now
from ghostrange_contracts.ghostdirector_m9 import DirectorPolicyId, ExperimentCampaignBudgetV1
from ghostrange_contracts.ghostledger_m7 import BundleMode
from ghostrange_contracts.scheduler_v3 import SchedulingContextV3

from ghostrange_contracts.adversarial_m8 import AdversarialVerificationReportV1

from ghostrange_adversarial.differential import interpret_differential
from ghostrange_adversarial.engine import run_adversarial_search
from ghostrange_adversarial.mutations import candidate_fingerprint
from ghostrange_adversarial.remediation_revision import propose_revision
from ghostrange_adversarial.scenarios.auth_admin_lab import AuthAdminLabScenario, build_auth_lab_plan
from ghostrange_adversarial.scenarios.billing_export_lab import (
    FIX_A_SHALLOW,
    FIX_B_DEEP,
    BillingTenantExportScenario,
    build_billing_export_lab_plan,
)
from ghostrange_adversarial.suite_evolution import promote_counterexample_to_regression
from ghostrange_director.director import GhostDirectorSimulator
from ghostrange_director.scenarios.auth_incident import build_auth_incident_knowledge
from ghostrange_director.scenarios.tenant_escalation import (
    TENANT_ESCALATION_MECHANICS,
    TRUE_MECHANISM as TENANT_ESCALATION_TRUE_MECHANISM,
    build_tenant_escalation_knowledge,
)
from ghostrange_director.scheduler_bridge import build_execution_dag
from ghostrange_ghostledger.seal import _minimal_manifest, seal_experiment
from ghostrange_ghostledger.signing import DevSigner
from ghostrange_ghostledger.verify import verify_bundle

ProviderMode = Literal["mock", "live", "not_run"]
GoldenScenarioId = Literal["tenant_escalation", "auth_incident"]


@dataclass
class GoldenPathBenchmark:
    compile_ms: int = 0
    director_ms: int = 0
    scheduler_ms: int = 0
    adversarial_ms: int = 0
    ledger_ms: int = 0
    total_ms: int = 0
    experiments_run: int = 0
    director_decisions: int = 0
    scheduler_decisions: int = 0
    counterexamples_confirmed: int = 0
    bundle_verified: bool = False
    live_mode: ProviderMode = "mock"
    correlation_id: str = ""

    def to_json(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class GoldenPathResult:
    investigation_id: uuid.UUID
    campaign_id: uuid.UUID
    range_id: uuid.UUID
    phases: list[str] = field(default_factory=list)
    benchmark: GoldenPathBenchmark = field(default_factory=GoldenPathBenchmark)
    bundle_digest: str | None = None
    errors: list[str] = field(default_factory=list)
    adversarial_report: AdversarialVerificationReportV1 | None = None
    remediation_id: uuid.UUID | None = None
    source_revision_id: uuid.UUID | None = None
    twin_revision_id: uuid.UUID | None = None
    # tenant_escalation only: the shallow-fix candidate's own search report, kept alongside
    # `adversarial_report` (which holds the *shipped* candidate's report — the deep fix) so
    # both halves of the remediation comparison survive the run. None for auth_incident.
    shallow_fix_adversarial_report: AdversarialVerificationReportV1 | None = None


class GoldenPathOrchestrator:
    """Single coordinated pipeline for mock (default) or live (explicit flag)."""

    def __init__(
        self,
        *,
        repo_root: Path,
        compose_path: Path | None = None,
        live: bool = False,
        scenario: GoldenScenarioId = "tenant_escalation",
    ) -> None:
        self.scenario = scenario
        self.repo_root = repo_root
        self.compose_path = compose_path or (
            repo_root / "ranges/ghostrange-auth-lab-v1/docker/vm-1/docker-compose.yml"
        )
        self.live = live

    def run(self, range_id: uuid.UUID | None = None) -> GoldenPathResult:
        t0 = time.perf_counter()
        range_id = range_id or uuid.uuid4()
        investigation_id = uuid.uuid4()
        campaign_id = uuid.uuid4()
        corr = hashlib.sha256(f"{investigation_id}:{campaign_id}".encode()).hexdigest()[:16]
        bench = GoldenPathBenchmark(
            correlation_id=corr,
            live_mode="live" if self.live else "mock",
        )
        result = GoldenPathResult(
            investigation_id=investigation_id,
            campaign_id=campaign_id,
            range_id=range_id,
            benchmark=bench,
        )

        # 1 — Compile authorized source
        t = time.perf_counter()
        compile_ok, compile_note = self._compile_source()
        bench.compile_ms = int((time.perf_counter() - t) * 1000)
        result.phases.append(f"compile:{compile_note}")

        # 2 — Director campaign
        t = time.perf_counter()
        if self.scenario == "auth_incident":
            knowledge = build_auth_incident_knowledge()
            director = GhostDirectorSimulator(true_mechanism="session_refresh_cache")
        else:
            knowledge = build_tenant_escalation_knowledge()
            director = GhostDirectorSimulator(
                true_mechanism=TENANT_ESCALATION_TRUE_MECHANISM,
                mechanics=TENANT_ESCALATION_MECHANICS,
                # Three real assets, not one shared "asset/gw01": billing-service,
                # api-gateway and (implicitly, never directly probed — see
                # tenant_escalation.py) identity-service all appear as distinct hypotheses.
                authorized_assets={"asset/gw01", "asset/billing01"},
            )
        knowledge.investigation_id = investigation_id
        campaign = director.run_campaign(
            knowledge,
            policy=DirectorPolicyId.GHOSTDIRECTOR_V1,
            budget=ExperimentCampaignBudgetV1(max_experiments=10, max_compute_usd=12),
            max_rounds=2,
        )
        bench.director_ms = int((time.perf_counter() - t) * 1000)
        bench.experiments_run = len(campaign.observations)
        bench.director_decisions = len(campaign.decisions)
        result.phases.append(f"director:stop={campaign.stop_reason}")

        if campaign.decisions and campaign.proposals:
            last_decision = campaign.decisions[-1]
            props = {p.id: p for p in campaign.proposals}
            selected = [props[pid] for pid in last_decision.selected_ids if pid in props]
            if selected:
                from ghostrange_contracts.ghostdirector_m9 import ExperimentPortfolioV1

                portfolio = ExperimentPortfolioV1(
                    campaign_id=campaign_id,
                    selected_proposal_ids=last_decision.selected_ids,
                )
                dag = build_execution_dag(campaign_id, portfolio, campaign.proposals)
                result.phases.append(f"director_dag:nodes={len(dag.nodes)}")

        # 3 — GhostScheduler V3 (plan only — HOW would run; no bypass)
        t = time.perf_counter()
        sched_note = self._scheduler_plan(range_id)
        bench.scheduler_ms = int((time.perf_counter() - t) * 1000)
        bench.scheduler_decisions = 1
        result.phases.append(f"scheduler:{sched_note}")

        # 4 — Adversarial verification (M8): try to break the fix.
        t = time.perf_counter()
        if self.scenario == "auth_incident":
            plan = build_auth_lab_plan()
            adv = run_adversarial_search(plan, AuthAdminLabScenario(remediated=True))
            bench.counterexamples_confirmed = len(adv.counterexamples)
            result.adversarial_report = adv
            result.phases.append(f"adversarial:{adv.phase.value}")
            result.remediation_id = uuid.uuid5(campaign_id, "fix-b.2")
        else:
            # Fix A (shallow): strips the config-drift header everyone found first
            # (X-Internal-Role) but nobody knew about the second, unrelated legacy
            # debug-bypass header — deterministic mutation search (mock mode: fixed
            # rng seed) rediscovers it. Fix A is FALSIFIED.
            plan_shallow = build_billing_export_lab_plan()
            adv_shallow = run_adversarial_search(
                plan_shallow, BillingTenantExportScenario(fix=FIX_A_SHALLOW), rng=random.Random(7)
            )
            result.phases.append(f"adversarial:shallow_fix={adv_shallow.phase.value}")
            result.shallow_fix_adversarial_report = adv_shallow

            # Fix B (deep): removes all header-based trust; the same search, run fresh
            # against this candidate, finds nothing before exhausting its strategies.
            # Fix B SURVIVES.
            plan_deep = build_billing_export_lab_plan(claim_id=plan_shallow.claim_id)
            adv_deep = run_adversarial_search(
                plan_deep, BillingTenantExportScenario(fix=FIX_B_DEEP), rng=random.Random(7)
            )
            result.phases.append(f"adversarial:deep_fix={adv_deep.phase.value}")

            bench.counterexamples_confirmed = len(adv_shallow.counterexamples) + len(adv_deep.counterexamples)
            # The candidate actually promoted downstream (GhostGate) is the one that
            # survived, not the falsified one.
            result.adversarial_report = adv_deep

            if adv_shallow.counterexamples:
                ce = adv_shallow.counterexamples[0]
                fp = candidate_fingerprint({"sequence": ce.action_sequence})
                diff = interpret_differential(
                    fingerprint=fp,
                    baseline_world_id=plan_shallow.world_id,
                    remediated_world_id=plan_deep.world_id,
                    baseline_satisfied=True,
                    remediated_satisfied=bool(adv_deep.counterexamples),
                )
                result.phases.append(f"differential:{diff.interpretation}")

                rev = propose_revision(
                    parent_remediation_id=uuid.uuid5(campaign_id, "fix-a-shallow"),
                    counterexample=ce,
                    parent_label="Fix A",
                )
                result.phases.append(f"remediation_revision:{rev.child_label}")
                result.remediation_id = uuid.uuid5(
                    campaign_id, rev.child_label.lower().replace(" ", "-").replace(".", "-")
                )

                suite_rev = promote_counterexample_to_regression(ce)
                result.phases.append(f"regression_suite:promoted={suite_rev.suite_id}")
            else:
                result.remediation_id = uuid.uuid5(campaign_id, "fix-b-deep")
        bench.adversarial_ms = int((time.perf_counter() - t) * 1000)
        if self.compose_path.is_file():
            compose_hash = hashlib.sha256(self.compose_path.read_bytes()).hexdigest()[:32]
            result.source_revision_id = uuid.uuid5(uuid.NAMESPACE_URL, f"source:{compose_hash}")
            result.twin_revision_id = uuid.uuid5(uuid.NAMESPACE_URL, f"twin:{compose_hash}:remediated")

        # 5 — GhostLedger seal + offline verify
        t = time.perf_counter()
        signer = DevSigner.generate()
        manifest = _minimal_manifest(
            investigation_objective="m10-golden-path",
            initiator="golden-path@ghostrange.local",
        )
        bundle, pem = seal_experiment(manifest, signer=signer, mode=BundleMode.FULL)
        v = verify_bundle(bundle, trusted_public_keys={signer.key_id: pem})
        bench.ledger_ms = int((time.perf_counter() - t) * 1000)
        bench.bundle_verified = v.verified_integrity
        result.bundle_digest = bundle.experiment_root.root_digest
        result.phases.append(f"ledger:verified={v.verified_integrity}")

        # 6 — Teardown (mock unless live)
        if self.live:
            result.phases.append("teardown:LIVE_NOT_IMPLEMENTED_IN_M10_SLICE")
            result.errors.append("live teardown must use coordinated lease + vultr-control")
        else:
            result.phases.append("teardown:mock_confirmed")

        bench.total_ms = int((time.perf_counter() - t0) * 1000)
        return result

    async def run_async(self, gateway, range_id: uuid.UUID | None = None) -> GoldenPathResult:
        """Run pipeline and emit SSE-compatible domain events."""
        result = self.run(range_id)
        corr = result.benchmark.correlation_id
        for i, phase in enumerate(result.phases):
            await gateway.append_legacy(
                result.range_id,
                {
                    "event_name": "golden_path.phase",
                    "schema_version": "1",
                    "occurred_at": utc_now().isoformat(),
                    "phase": phase,
                    "index": i,
                    "correlation_id": corr,
                    "investigation_id": str(result.investigation_id),
                },
                source="golden_path",
            )
        await gateway.append_legacy(
            result.range_id,
            {
                "event_name": "director.decision",
                "schema_version": "1",
                "occurred_at": utc_now().isoformat(),
                "decisions": result.benchmark.director_decisions,
                "experiments_run": result.benchmark.experiments_run,
                "correlation_id": corr,
            },
            source="ghostdirector",
        )
        await gateway.append_legacy(
            result.range_id,
            {
                "event_name": "scheduler.plan",
                "schema_version": "1",
                "occurred_at": utc_now().isoformat(),
                "scheduler_decisions": result.benchmark.scheduler_decisions,
                "correlation_id": corr,
            },
            source="ghostscheduler",
        )
        if result.bundle_digest:
            await gateway.append_legacy(
                result.range_id,
                {
                    "event_name": "ghostledger.sealed",
                    "schema_version": "1",
                    "occurred_at": utc_now().isoformat(),
                    "root_digest": result.bundle_digest,
                    "verified": result.benchmark.bundle_verified,
                },
                source="ghostledger",
            )
        return result

    def _compile_source(self) -> tuple[bool, str]:
        if not self.compose_path.is_file():
            return False, "missing_compose"
        try:
            from ghostrange_range_compiler.pipeline import RangeCompiler

            rc = RangeCompiler()
            out = rc.compile_compose(self.compose_path)
            n = len(out.graph.nodes) if out.graph else 0
            return True, f"nodes={n}"
        except Exception as exc:
            return False, f"compile_error:{exc.__class__.__name__}"

    def _scheduler_plan(self, range_id: uuid.UUID) -> str:
        try:
            from ghostrange_scheduler.v3.plan import plan

            ctx = SchedulingContextV3(
                range_id=range_id,
                tasks=[],
                workers=[],
                dependency_edges=[],
                budget_remaining_usd=25.0,
                budget_hard_cap_usd=50.0,
            )
            p = plan(ctx)
            return f"actions={len(p.actions)}"
        except Exception as exc:
            return f"fallback:{exc.__class__.__name__}"


def assert_live_allowed() -> None:
    import os

    if os.environ.get("GHOSTRANGE_LIVE", "").lower() not in ("1", "true", "yes"):
        raise RuntimeError("GHOSTRANGE_LIVE must be true for live golden path")
    if not os.environ.get("VULTR_API_KEY"):
        raise RuntimeError("VULTR_API_KEY required for live golden path")


__all__ = ["GoldenPathOrchestrator", "GoldenPathResult", "GoldenPathBenchmark", "assert_live_allowed"]
