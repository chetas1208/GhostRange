"""External deployment record ingress — M11 hook → GhostWatch."""

from __future__ import annotations

import hashlib
import uuid

from ghostrange_contracts.ghostwatch_m12 import (
    ExternalDeploymentRecordV1,
    GhostWatchCampaignState,
    TwinPredictionV1,
)
from ghostrange_contracts._base import utc_now

from .conformance import compare_deployment


class IngestError(Exception):
    pass


def verify_external_record(
    record: ExternalDeploymentRecordV1,
    *,
    expected_change_hash: str,
    expected_campaign_id: uuid.UUID,
) -> None:
    if record.campaign_id and record.campaign_id != expected_campaign_id:
        raise IngestError("campaign_id mismatch")
    if record.approved_change_hash and record.approved_change_hash != expected_change_hash:
        raise IngestError("approved_change_hash mismatch — reject spoofed deployment event")
    if record.sequence < 0:
        raise IngestError("invalid sequence")


def apply_external_record(
    campaign,
    record: ExternalDeploymentRecordV1,
    *,
    policy_hold_on_unknown: bool = True,
    seen_events: set[str] | None = None,
):
    """Update campaign from authenticated external status (idempotent by event_id)."""
    from ghostrange_contracts.ghostwatch_m12 import GhostWatchCampaignV1

    camp: GhostWatchCampaignV1 = campaign
    seen = seen_events if seen_events is not None else set()
    if record.event_id:
        key = f"evt:{record.event_id}"
        if key in seen:
            return camp, ["deployment.duplicate_ignored"]
        seen.add(key)

    if record.sequence < camp.event_sequence:
        return camp, ["deployment.out_of_order_ignored"]

    camp.event_sequence = max(camp.event_sequence, record.sequence)
    camp.execution.observed_at = utc_now()
    if record.stage:
        camp.execution.current_stage = record.stage
    if record.exposure:
        camp.execution.current_exposure = record.exposure

    conf = compare_deployment(
        camp.approved_artifact_digest,
        record.observed_state,
    )
    camp.conformance = conf
    camp.updated_at = utc_now()
    events = ["deployment.observed", "deployment.conformance_checked"]
    if conf.status.value == "MATERIAL_DIFFERENCE":
        camp.state = GhostWatchCampaignState.HOLD
        events.append("deployment.variance_detected")
    elif conf.status.value == "UNKNOWN" and policy_hold_on_unknown:
        camp.state = GhostWatchCampaignState.HOLD
        events.append("rollout.hold")
    else:
        camp.state = GhostWatchCampaignState.OBSERVING
    if record.stage:
        events.append("deployment.stage_changed")
    return camp, events


def capture_twin_prediction(campaign, *, expected_digest: str, behavior_summary: str):
    from ghostrange_contracts.ghostwatch_m12 import TwinPredictionV1

    campaign.twin_prediction = TwinPredictionV1(
        promotion_candidate_id=campaign.promotion_candidate_id,
        expected_artifact_digest=expected_digest,
        expected_behavior_summary=behavior_summary,
    )
    return campaign
