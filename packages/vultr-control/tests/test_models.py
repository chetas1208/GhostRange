from __future__ import annotations

import pytest
from pydantic import ValidationError

from ghostrange_vultr_control import CreateComputeRequest, GhostRangeTags


class TestGhostRangeTagsRoundTrip:
    def test_vultr_tag_list_round_trip(self):
        tags = GhostRangeTags(range_id="range-1", world_id="world-1", ttl_seconds=3600)
        rendered = tags.as_vultr_tag_list()
        assert rendered == [
            "ghostrange:created_by:ghostrange",
            "ghostrange:range_id:range-1",
            "ghostrange:world_id:world-1",
            "ghostrange:ttl_seconds:3600",
        ]
        parsed = GhostRangeTags.from_vultr_tag_list(rendered)
        assert parsed == tags

    def test_vultr_tag_list_round_trip_minimal(self):
        tags = GhostRangeTags(range_id="range-1")
        rendered = tags.as_vultr_tag_list()
        parsed = GhostRangeTags.from_vultr_tag_list(rendered)
        assert parsed == tags
        assert parsed.world_id is None
        assert parsed.ttl_seconds is None

    def test_vultr_tag_list_ignores_foreign_tags(self):
        rendered = ["someone-elses-tag", "env:prod", "ghostrange:created_by:ghostrange", "ghostrange:range_id:range-1"]
        parsed = GhostRangeTags.from_vultr_tag_list(rendered)
        assert parsed == GhostRangeTags(range_id="range-1")

    def test_vultr_tag_list_returns_none_when_not_ghostrange_owned(self):
        assert GhostRangeTags.from_vultr_tag_list(["prod", "team:infra"]) is None
        assert GhostRangeTags.from_vultr_tag_list([]) is None

    def test_description_round_trip(self):
        tags = GhostRangeTags(range_id="range-1", world_id="world-1", ttl_seconds=1800)
        rendered = tags.as_description()
        assert rendered.startswith("ghostrange;")
        parsed = GhostRangeTags.from_description(rendered)
        assert parsed == tags

    def test_description_round_trip_minimal(self):
        tags = GhostRangeTags(range_id="range-1")
        parsed = GhostRangeTags.from_description(tags.as_description())
        assert parsed == tags

    def test_description_returns_none_for_foreign_description(self):
        assert GhostRangeTags.from_description("hand-created by ops, do not touch") is None
        assert GhostRangeTags.from_description("") is None
        assert GhostRangeTags.from_description(None) is None

    def test_description_returns_none_when_missing_range_id(self):
        # a ghostrange-namespaced description that's missing the required key
        assert GhostRangeTags.from_description("ghostrange;created_by=ghostrange") is None


class TestGhostRangeTagsValidation:
    def test_range_id_required(self):
        with pytest.raises(ValidationError):
            GhostRangeTags()  # type: ignore[call-arg]

    def test_negative_ttl_rejected(self):
        with pytest.raises(ValidationError):
            GhostRangeTags(range_id="range-1", ttl_seconds=-1)

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            GhostRangeTags(range_id="range-1", not_a_real_field="x")  # type: ignore[call-arg]


class TestCreateComputeRequestValidation:
    def test_requires_exactly_one_boot_source(self, tags):
        with pytest.raises(ValidationError):
            CreateComputeRequest(world_ref="vpc-1", region="ewr", plan="vc2-1c-1gb", tags=tags)

    def test_rejects_both_os_id_and_snapshot_id(self, tags):
        with pytest.raises(ValidationError):
            CreateComputeRequest(
                world_ref="vpc-1", region="ewr", plan="vc2-1c-1gb", tags=tags, os_id=387, snapshot_id="snap-1"
            )

    def test_accepts_os_id_only(self, tags):
        req = CreateComputeRequest(world_ref="vpc-1", region="ewr", plan="vc2-1c-1gb", tags=tags, os_id=387)
        assert req.os_id == 387
        assert req.snapshot_id is None

    def test_accepts_snapshot_id_only(self, tags):
        req = CreateComputeRequest(world_ref="vpc-1", region="ewr", plan="vc2-1c-1gb", tags=tags, snapshot_id="snap-1")
        assert req.snapshot_id == "snap-1"
        assert req.os_id is None
