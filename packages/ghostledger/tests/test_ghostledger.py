import json
from pathlib import Path

import pytest

from ghostrange_contracts.ghostledger_m7 import BundleMode, GhostBundleV1
from ghostrange_ghostledger.artifact_store import ContentAddressedArtifactStore
from ghostrange_ghostledger.canonical import digest_sha256
from ghostrange_ghostledger.event_chain import verify_event_chain
from ghostrange_ghostledger.seal import _minimal_manifest, seal_experiment
from ghostrange_ghostledger.signing import DevSigner
from ghostrange_ghostledger.verify import verify_bundle

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "bundles"


def test_seal_and_verify_roundtrip():
    signer = DevSigner.generate()
    manifest = _minimal_manifest()
    bundle, pem = seal_experiment(manifest, signer=signer, artifact_digests=["sha256:" + "c" * 64])
    result = verify_bundle(bundle, trusted_public_keys={signer.key_id: pem})
    assert result.verified_integrity is True
    assert result.signature_valid.value == "PASS"


def test_manifest_tamper_detected():
    signer = DevSigner.generate()
    bundle, pem = seal_experiment(_minimal_manifest(), signer=signer)
    tampered = bundle.model_copy(
        update={
            "manifest": bundle.manifest.model_copy(
                update={"investigation_objective": "tampered"},
            ),
        },
    )
    result = verify_bundle(tampered, trusted_public_keys={signer.key_id: pem})
    assert result.verified_integrity is False
    assert any("manifest" in f for f in result.failures)


def test_event_chain_tamper():
    signer = DevSigner.generate()
    bundle, pem = seal_experiment(_minimal_manifest(), signer=signer)
    log = list(bundle.event_log)
    log[0] = {**log[0], "type": "mutated"}
    tampered = bundle.model_copy(update={"event_log": log})
    result = verify_bundle(tampered, trusted_public_keys={signer.key_id: pem})
    assert result.verified_integrity is False


def test_content_addressed_store(tmp_path):
    store = ContentAddressedArtifactStore(tmp_path / "objects")
    d = store.put(b"evidence-bytes")
    assert store.exists(d)
    assert store.get(d) == b"evidence-bytes"
    bad = tmp_path / "objects" / "sha256" / d[7:9] / d[7:]
    bad.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="digest mismatch"):
        store.get(d)


def test_canonical_manifest_hash_stable():
    m1 = _minimal_manifest()
    m2 = _minimal_manifest()
    m2.experiment.run_id = m1.experiment.run_id
    m2.manifest_id = m1.manifest_id
    m2.started_at = m1.started_at
    m2.source_revision_id = m1.source_revision_id
    m2.twin_revision_id = m1.twin_revision_id
    m2.fidelity_profile_id = m1.fidelity_profile_id
    assert digest_sha256(m1) == digest_sha256(m2)


def _write_golden(name: str, bundle: GhostBundleV1, pem: str) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    payload = {
        "bundle": json.loads(bundle.model_dump_json()),
        "trusted_public_keys": {bundle.attestation.key_id: pem},
    }
    (FIXTURES / name).write_text(json.dumps(payload, indent=2))


def test_write_valid_full_fixture():
    signer = DevSigner.generate()
    bundle, pem = seal_experiment(
        _minimal_manifest(),
        signer=signer,
        mode=BundleMode.FULL,
        artifact_digests=["sha256:" + "d" * 64],
    )
    _write_golden("valid-full.json", bundle, pem)
    loaded = json.loads((FIXTURES / "valid-full.json").read_text())
    b = GhostBundleV1.model_validate(loaded["bundle"])
    assert verify_bundle(b, trusted_public_keys=loaded["trusted_public_keys"]).verified_integrity


def test_write_tampered_manifest_fixture():
    signer = DevSigner.generate()
    bundle, pem = seal_experiment(_minimal_manifest(), signer=signer, mode=BundleMode.THIN)
    bundle_dict = json.loads(bundle.model_dump_json())
    bundle_dict["manifest"]["investigation_objective"] = "tampered"
    payload = {"bundle": bundle_dict, "trusted_public_keys": {signer.key_id: pem}}
    FIXTURES.mkdir(parents=True, exist_ok=True)
    (FIXTURES / "tampered-manifest.json").write_text(json.dumps(payload, indent=2))
    b = GhostBundleV1.model_validate(payload["bundle"])
    assert verify_bundle(b, trusted_public_keys=payload["trusted_public_keys"]).verified_integrity is False


def test_event_chain_helper():
    from ghostrange_ghostledger.event_chain import chain_events

    chained, root = chain_events([{"type": "a"}, {"type": "b"}])
    assert verify_event_chain(chained)
    assert chained[-1]["event_hash"] == root
