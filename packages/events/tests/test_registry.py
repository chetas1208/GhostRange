from ghostrange_events.names import EventName
from ghostrange_events.registry import EVENT_REGISTRY


def test_every_event_name_has_exactly_one_payload_schema():
    all_names = set(EventName)
    registered_names = set(EVENT_REGISTRY.keys())
    assert all_names == registered_names, (
        f"missing: {all_names - registered_names}, "
        f"extra/unknown: {registered_names - all_names}"
    )
    # dict keys are inherently unique, but assert explicitly so the
    # invariant is documented as a test, not an accident of data structure.
    assert len(EVENT_REGISTRY) == len(EventName)


def test_each_payload_classs_own_event_name_matches_its_registry_key():
    for event_name, payload_cls in EVENT_REGISTRY.items():
        assert payload_cls.EVENT_NAME == event_name
        default_value = payload_cls.model_fields["event_name"].default
        assert default_value == event_name


def test_no_two_event_names_share_a_payload_class():
    payload_classes = list(EVENT_REGISTRY.values())
    assert len(payload_classes) == len(set(payload_classes))
