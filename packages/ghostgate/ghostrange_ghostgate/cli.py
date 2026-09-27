"""CLI — prepare / inspect / export / approve (human context required)."""

from __future__ import annotations

import argparse
import json
import sys
import uuid

from ghostrange_contracts.adversarial_m8 import AdversarialBudgetV1, AdversarialVerificationReportV1, SearchPolicyId, SearchStopReason
from ghostrange_contracts.adversarial_m8 import AdversarialClaimPhase

from .approval import create_approval_request, record_human_approval
from .promote import GhostGate, PromotionPrepareInput


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ghostrange-promotion")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prepare = sub.add_parser("prepare", help="Build promotion candidate from experiment")
    p_prepare.add_argument("--experiment-id", required=True)
    p_prepare.add_argument("--evidence-digest", default="sha256:demo")

    p_inspect = sub.add_parser("inspect", help="Show candidate JSON")
    p_inspect.add_argument("candidate_id")

    p_export = sub.add_parser("export", help="Export promotion bundle JSON")
    p_export.add_argument("candidate_id")

    p_approve = sub.add_parser("approve", help="Record human approval (requires --approver-id)")
    p_approve.add_argument("candidate_id")
    p_approve.add_argument("--approver-id", required=True)

    args = parser.parse_args(argv)
    gate = GhostGate()

    if args.cmd == "prepare":
        exp = uuid.UUID(args.experiment_id)
        demo_adv = AdversarialVerificationReportV1(
            claim_id=uuid.uuid4(),
            search_run_id=uuid.uuid4(),
            phase=AdversarialClaimPhase.HARDENED_VERIFIED,
            budget=AdversarialBudgetV1(max_attempts=2104),
            search_policy=SearchPolicyId.GHOSTSCHEDULER_SEARCH,
            attempts=2104,
            stop_reason=SearchStopReason.BUDGET_EXHAUSTED,
        )
        res = gate.prepare(
            PromotionPrepareInput(
                experiment_id=exp,
                remediation_id=uuid.uuid4(),
                source_revision_id=uuid.uuid4(),
                twin_revision_id=uuid.uuid4(),
                evidence_root_digest=args.evidence_digest,
                adversarial=demo_adv,
            )
        )
        print(json.dumps({"candidate_id": str(res.candidate.id), "state": res.candidate.state.value, "events": res.events}, indent=2))
        return 0

    cid = uuid.UUID(args.candidate_id)
    if args.cmd == "inspect":
        cand = gate.get(cid)
        if not cand:
            print("not found", file=sys.stderr)
            return 1
        print(cand.model_dump_json(indent=2))
        return 0

    if args.cmd == "export":
        print(gate.export_bundle(cid))
        return 0

    if args.cmd == "approve":
        cand = gate.get(cid)
        if not cand:
            print("not found", file=sys.stderr)
            return 1
        req = create_approval_request(cand, summary="CLI approval")
        dec = record_human_approval(
            req,
            approver_id=args.approver_id,
            candidate_hash=cand.change_candidate_hash,
        )
        print(dec.model_dump_json(indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
