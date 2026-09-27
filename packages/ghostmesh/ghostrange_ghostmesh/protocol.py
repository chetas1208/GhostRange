"""GhostMeshProtocolV1 — versioned envelopes; no arbitrary RPC."""

from __future__ import annotations

import hashlib
import json

from ghostrange_contracts.ghostmesh_m13 import (
    GhostMeshProtocolEnvelopeV1,
    MeshProtocolMessageKind,
)


def wrap_message(
    *,
    federation_id: str,
    sender_node_id: str,
    message_kind: MeshProtocolMessageKind,
    payload: dict,
    signature: str = "",
) -> GhostMeshProtocolEnvelopeV1:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return GhostMeshProtocolEnvelopeV1(
        federation_id=federation_id,
        sender_node_id=sender_node_id,
        message_kind=message_kind,
        message_id=digest[:32],
        payload_digest=digest,
        signature=signature,
    )
