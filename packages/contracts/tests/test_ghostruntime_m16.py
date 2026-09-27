import pytest
from uuid import uuid4

from ghostrange_contracts.ghostruntime_m16 import (
    CampaignRuntimeState,
    CanonicalCampaignStateV1,
    DeterministicRuntimeReplayV1,
    RuntimeEventV1,
)


def test_canonical_campaign_state_defaults():
    cid, rid = uuid4(), uuid4()
    st = CanonicalCampaignStateV1(campaign_id=cid, range_id=rid, budget_hard_cap_usd=25.0)
    assert st.lifecycle == CampaignRuntimeState.CREATED
    assert st.runtime_revision == 0
    assert st.budget_spent_usd == 0.0


def test_runtime_event_sequence_unique_per_aggregate():
    cid, agg = uuid4(), uuid4()
    ev = RuntimeEventV1(campaign_id=cid, aggregate_id=agg, sequence=1, event_type="worker.created")
    assert ev.event_id is not None


def test_replay_sequence_order():
    with pytest.raises(ValueError):
        DeterministicRuntimeReplayV1(campaign_id=uuid4(), from_sequence=5, to_sequence=2)
