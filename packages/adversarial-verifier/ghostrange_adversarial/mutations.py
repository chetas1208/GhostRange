"""Typed mutation operators — policy constrained."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterator

from ghostrange_contracts.adversarial_m8 import (
    MutationKind,
    MutationOperatorV1,
    SearchArmKind,
    SearchCandidateV1,
)

HEADER_CANDIDATES = [
    ("X-Forwarded-User", "admin"),
    ("X-Internal-Role", "admin"),
    ("X-Debug-Auth", "bypass"),
    ("X-Original-URL", "/admin"),
    ("Authorization", "Bearer invalid"),
]

PATH_VARIANTS = ["/admin", "/admin/", "/admin%2f", "/Admin", "/api/../admin"]

IDENTITIES = ["anonymous", "expired", "wrong-role"]


def candidate_fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def generate_candidates(
    *,
    world_asset_id: str,
    arms: list[SearchArmKind],
    base_path: str = "/admin",
) -> Iterator[SearchCandidateV1]:
    if SearchArmKind.HEADER_MUTATION in arms:
        for name, value in HEADER_CANDIDATES:
            headers = {name: value}
            seq = [{"method": "GET", "path": base_path, "headers": headers, "identity": "anonymous"}]
            fp = candidate_fingerprint({"arm": "header", "headers": headers, "path": base_path})
            yield SearchCandidateV1(
                fingerprint=fp,
                world_asset_id=world_asset_id,
                arm=SearchArmKind.HEADER_MUTATION,
                operators=[
                    MutationOperatorV1(kind=MutationKind.HEADER, arm=SearchArmKind.HEADER_MUTATION, parameters={"name": name, "value": value})
                ],
                action_sequence=seq,
            )

    if SearchArmKind.PATH_VARIATION in arms:
        for path in PATH_VARIANTS:
            seq = [{"method": "GET", "path": path, "headers": {}, "identity": "anonymous"}]
            fp = candidate_fingerprint({"arm": "path", "path": path})
            yield SearchCandidateV1(
                fingerprint=fp,
                world_asset_id=world_asset_id,
                arm=SearchArmKind.PATH_VARIATION,
                operators=[MutationOperatorV1(kind=MutationKind.PATH, arm=SearchArmKind.PATH_VARIATION, parameters={"path": path})],
                action_sequence=seq,
            )

    if SearchArmKind.IDENTITY_STATE in arms:
        for ident in IDENTITIES:
            seq = [{"method": "GET", "path": base_path, "headers": {}, "identity": ident}]
            fp = candidate_fingerprint({"arm": "identity", "identity": ident})
            yield SearchCandidateV1(
                fingerprint=fp,
                world_asset_id=world_asset_id,
                arm=SearchArmKind.IDENTITY_STATE,
                operators=[
                    MutationOperatorV1(kind=MutationKind.IDENTITY_STATE, arm=SearchArmKind.IDENTITY_STATE, parameters={"identity": ident})
                ],
                action_sequence=seq,
            )


__all__ = ["generate_candidates", "candidate_fingerprint", "HEADER_CANDIDATES"]
