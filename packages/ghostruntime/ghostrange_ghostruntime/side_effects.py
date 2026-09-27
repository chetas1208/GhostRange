"""Side-effect intent pattern: persist before external call."""

from __future__ import annotations

from ghostrange_contracts.ghostruntime_m16 import (
    IdempotencyKeyV1,
    SideEffectRecordV1,
    SideEffectStatus,
)


def persist_intent_before_effect(
    *,
    campaign_id,
    operation: str,
    target: str,
    idempotency_key: str,
    scope: str,
    intent_revision: int,
) -> SideEffectRecordV1:
    """Pure contract helper — storage layer assigns effect_id and writes PG row."""
    return SideEffectRecordV1(
        idempotency_key=IdempotencyKeyV1(key=idempotency_key, scope=scope, campaign_id=campaign_id),
        campaign_id=campaign_id,
        operation=operation,
        target=target,
        intent_revision=intent_revision,
        status=SideEffectStatus.INTENDED,
    )
