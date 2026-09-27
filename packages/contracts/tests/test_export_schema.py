import json

import ghostrange_contracts as contracts
from ghostrange_contracts.export_schema import _iter_model_classes, export_all


def test_export_all_writes_a_schema_for_every_model(tmp_path):
    written = export_all(tmp_path)
    model_classes = list(_iter_model_classes())
    assert len(written) == len(model_classes)
    assert len(written) > 20  # sanity: we expect a real, non-trivial set of models

    names_written = {p.stem for p in written}
    names_expected = {cls.__name__ for cls in model_classes}
    assert names_written == names_expected


def test_exported_schema_is_valid_json_with_expected_keys(tmp_path):
    export_all(tmp_path)
    schema_path = tmp_path / "TaskV1.json"
    assert schema_path.exists()
    schema = json.loads(schema_path.read_text())
    assert schema["title"] == "TaskV1"
    assert "properties" in schema
    assert "resource_profile" in schema["properties"]


def test_every_public_model_is_reachable_from_package_root():
    # Guards against a model being added to a module but forgotten in
    # __init__.py's __all__, which would silently exclude it from schema
    # export.
    assert "RangeSpecV1" in contracts.__all__
    assert "SchedulerDecisionV1" in contracts.__all__
    assert "EvidenceV1" in contracts.__all__
    assert "TaskV1" in contracts.__all__
    assert "WorldV1" in contracts.__all__
