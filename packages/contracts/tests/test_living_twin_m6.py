from ghostrange_contracts.living_twin_m6 import (
    DriftSetV1,
    SourceRevisionV1,
    ClaimValidityStatus,
)


def test_source_revision():
    r = SourceRevisionV1(source_id=__import__("uuid").uuid4(), source_hash="abc")
    assert r.schema_version == "1"


def test_claim_validity_enum():
    assert ClaimValidityStatus.STALE.value == "STALE"
