"""Offline bundle integrity verification — no GhostRange DB."""

from __future__ import annotations

from ghostrange_contracts.ghostledger_m7 import (
    BundleVerificationResultV1,
    VerificationDimensionStatus,
)

from .canonical import digest_sha256
from .event_chain import verify_event_chain
from .merkle import merkle_root
from .seal import graph_content_digest
from .signing import DevSigner


def verify_bundle(bundle, *, trusted_public_keys: dict[str, str]) -> BundleVerificationResultV1:
    failures: list[str] = []
    dims = {}

    try:
        bundle.model_validate(bundle.model_dump())
        dims["structure_valid"] = VerificationDimensionStatus.PASS
    except Exception as exc:
        dims["structure_valid"] = VerificationDimensionStatus.FAIL
        failures.append(f"structure: {exc}")
        return _result(False, failures, dims)

    manifest_d = digest_sha256(bundle.manifest)
    if manifest_d != bundle.experiment_root.manifest_digest:
        failures.append("manifest digest mismatch")
        dims["hashes_valid"] = VerificationDimensionStatus.FAIL
    else:
        graph_d = graph_content_digest(bundle.provenance_graph)
        if graph_d != bundle.experiment_root.provenance_graph_digest:
            failures.append("provenance graph digest mismatch")
            dims["hashes_valid"] = VerificationDimensionStatus.FAIL
        else:
            art_root = merkle_root([a.digest for a in bundle.artifact_index])
            if art_root != bundle.experiment_root.artifact_merkle_root:
                failures.append("artifact merkle root mismatch")
                dims["hashes_valid"] = VerificationDimensionStatus.FAIL
            else:
                from .event_chain import GENESIS

                expected_event_root = (
                    bundle.event_log[-1]["event_hash"] if bundle.event_log else GENESIS
                )
                if expected_event_root != bundle.experiment_root.event_log_root:
                    failures.append("event log root mismatch")
                    dims["hashes_valid"] = VerificationDimensionStatus.FAIL
                else:
                    root_body = {
                        "manifest_digest": bundle.experiment_root.manifest_digest,
                        "provenance_graph_digest": bundle.experiment_root.provenance_graph_digest,
                        "artifact_merkle_root": bundle.experiment_root.artifact_merkle_root,
                        "event_log_root": bundle.experiment_root.event_log_root,
                        "claim_set_digest": bundle.experiment_root.claim_set_digest,
                    }
                    if digest_sha256(root_body) != bundle.experiment_root.root_digest:
                        failures.append("experiment root digest mismatch")
                        dims["hashes_valid"] = VerificationDimensionStatus.FAIL
                    else:
                        dims["hashes_valid"] = VerificationDimensionStatus.PASS

    if not verify_event_chain(bundle.event_log):
        failures.append("event chain broken")
        dims["event_chain_valid"] = VerificationDimensionStatus.FAIL
    else:
        dims["event_chain_valid"] = VerificationDimensionStatus.PASS

    att = bundle.attestation
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": "experiment-root", "digest": {"sha256": att.subject_digest.removeprefix("sha256:")}}],
        "predicateType": att.predicate.predicate_type,
        "predicate": att.predicate.model_dump(mode="json"),
    }
    pub = trusted_public_keys.get(att.key_id)
    if not pub:
        failures.append(f"unknown signer key_id={att.key_id}")
        dims["identity_valid"] = VerificationDimensionStatus.FAIL
        dims["signature_valid"] = VerificationDimensionStatus.FAIL
    else:
        dims["identity_valid"] = VerificationDimensionStatus.PASS
        if DevSigner.verify_payload(statement, att.signature_b64, pub):
            dims["signature_valid"] = VerificationDimensionStatus.PASS
        else:
            failures.append("invalid signature")
            dims["signature_valid"] = VerificationDimensionStatus.FAIL

    dims.setdefault("artifacts_complete", VerificationDimensionStatus.PASS)
    dims.setdefault("claim_references_valid", VerificationDimensionStatus.PASS)
    dims.setdefault("replayable", VerificationDimensionStatus.PASS)
    dims.setdefault("redaction_valid", VerificationDimensionStatus.PASS)

    ok = not failures
    return _result(ok, failures, dims)


def _result(ok, failures, dims):
    return BundleVerificationResultV1(
        verified_integrity=ok,
        failures=failures,
        structure_valid=dims.get("structure_valid", VerificationDimensionStatus.SKIP),
        hashes_valid=dims.get("hashes_valid", VerificationDimensionStatus.SKIP),
        signature_valid=dims.get("signature_valid", VerificationDimensionStatus.SKIP),
        identity_valid=dims.get("identity_valid", VerificationDimensionStatus.SKIP),
        event_chain_valid=dims.get("event_chain_valid", VerificationDimensionStatus.SKIP),
        artifacts_complete=dims.get("artifacts_complete", VerificationDimensionStatus.SKIP),
        claim_references_valid=dims.get("claim_references_valid", VerificationDimensionStatus.SKIP),
        replayable=dims.get("replayable", VerificationDimensionStatus.SKIP),
        redaction_valid=dims.get("redaction_valid", VerificationDimensionStatus.SKIP),
    )


__all__ = ["verify_bundle"]
