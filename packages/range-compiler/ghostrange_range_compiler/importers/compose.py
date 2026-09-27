"""Docker Compose importer — YAML parse, no secret value retention."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from ghostrange_contracts.source_model import (
    SourceFileRefV1,
    SourceModelV1,
    SourceResourceRecordV1,
    SourceType,
    SourceWarningV1,
    UnsupportedConstructStatus,
)
from ghostrange_contracts.system_graph import (
    GraphEdgeKind,
    GraphNodeKind,
    NormalizedEdgeV1,
    NormalizedNodeV1,
    NormalizedSystemGraphV1,
    SourceProvenanceV1,
)

PARSER_ID = "ghostrange.importer.compose"
PARSER_VERSION = "0.1.0"

_SECRET_ENV_PATTERNS = ("SECRET", "PASSWORD", "TOKEN", "API_KEY", "PRIVATE_KEY")


def _file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_compose_file(path: Path) -> SourceModelV1:
    content = path.read_bytes()
    data: dict[str, Any] = yaml.safe_load(content) or {}
    services: dict[str, Any] = data.get("services") or {}
    networks = list((data.get("networks") or {}).keys())
    volumes = list((data.get("volumes") or {}).keys())

    resources: list[SourceResourceRecordV1] = []
    images: list[str] = []
    secret_refs: list[str] = []
    warnings: list[SourceWarningV1] = []

    for name, svc in services.items():
        if not isinstance(svc, dict):
            warnings.append(
                SourceWarningV1(
                    code="INVALID_SERVICE",
                    message=f"service {name} is not a mapping",
                    source_location=f"{path}:services.{name}",
                    status=UnsupportedConstructStatus.UNSUPPORTED_REQUIRED,
                )
            )
            continue
        img = svc.get("image")
        if img:
            images.append(str(img))
        loc = f"{path}:services.{name}"
        resources.append(
            SourceResourceRecordV1(
                construct_type="compose_service",
                construct_name=name,
                source_location=loc,
                raw_attributes={
                    k: v
                    for k, v in svc.items()
                    if k not in ("environment", "secrets")
                },
            )
        )
        env = svc.get("environment") or {}
        if isinstance(env, dict):
            for ek, ev in env.items():
                key_upper = str(ek).upper()
                if any(p in key_upper for p in _SECRET_ENV_PATTERNS):
                    secret_refs.append(f"{name}.env.{ek}")
                    if ev and not str(ev).startswith("${"):
                        warnings.append(
                            SourceWarningV1(
                                code="PLAINTEXT_SECRET_ENV",
                                message=f"Plaintext env {ek} on service {name} — value not stored",
                                source_location=loc,
                                status=UnsupportedConstructStatus.UNSUPPORTED_REQUIRED,
                            )
                        )
        if svc.get("privileged"):
            warnings.append(
                SourceWarningV1(
                    code="PRIVILEGED_CONTAINER",
                    message=f"Service {name} requests privileged mode",
                    source_location=loc,
                    status=UnsupportedConstructStatus.UNSUPPORTED_REQUIRED,
                )
            )
        if svc.get("network_mode") == "host":
            warnings.append(
                SourceWarningV1(
                    code="HOST_NETWORK",
                    message=f"Service {name} uses host network",
                    source_location=loc,
                    status=UnsupportedConstructStatus.UNSUPPORTED_REQUIRED,
                )
            )

    return SourceModelV1(
        source_type=SourceType.DOCKER_COMPOSE,
        files=[
            SourceFileRefV1(
                path=str(path),
                content_hash=_file_hash(content),
                byte_size=len(content),
            )
        ],
        resources=resources,
        services=list(services.keys()),
        networks=networks,
        volumes=volumes,
        images=images,
        secrets_references=secret_refs,
        warnings=warnings,
        parser_id=PARSER_ID,
        parser_version=PARSER_VERSION,
        metadata={"compose_version": str(data.get("version", "implicit-v3"))},
    )


def compose_to_graph(source: SourceModelV1, path: Path) -> NormalizedSystemGraphV1:
    content = path.read_bytes()
    data: dict[str, Any] = yaml.safe_load(content) or {}
    services: dict[str, Any] = data.get("services") or {}
    network_names = list((data.get("networks") or {}).keys())

    nodes: list[NormalizedNodeV1] = []
    edges: list[NormalizedEdgeV1] = []
    prov_base = SourceProvenanceV1(
        source_file=str(path),
        source_construct="",
        source_location="",
        parser_id=PARSER_ID,
    )

    net_ids: dict[str, Any] = {}
    for nn in network_names:
        nid = NormalizedNodeV1(
            name=nn,
            kind=GraphNodeKind.NETWORK,
            provenance=prov_base.model_copy(
                update={"source_construct": f"networks.{nn}", "source_location": f"{path}:networks.{nn}"}
            ),
        )
        net_ids[nn] = nid.id
        nodes.append(nid)

    svc_ids: dict[str, Any] = {}
    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        kind = GraphNodeKind.GATEWAY if name in ("gateway", "nginx") else GraphNodeKind.SERVICE
        if "postgres" in str(svc.get("image", "")).lower() or name in ("db", "database", "data-store"):
            kind = GraphNodeKind.DATABASE
        node = NormalizedNodeV1(
            name=name,
            kind=kind,
            labels={"image": str(svc.get("image", ""))},
            attributes={"ports": str(svc.get("ports", []))},
            provenance=prov_base.model_copy(
                update={
                    "source_construct": f"services.{name}",
                    "source_location": f"{path}:services.{name}",
                }
            ),
        )
        svc_ids[name] = node.id
        nodes.append(node)
        for net in svc.get("networks") or []:
            net_key = net if isinstance(net, str) else net
            if isinstance(net, dict):
                net_key = list(net.keys())[0] if net else ""
            if net_key in net_ids:
                edges.append(
                    NormalizedEdgeV1(
                        from_node_id=node.id,
                        to_node_id=net_ids[net_key],
                        kind=GraphEdgeKind.MEMBER_OF_NETWORK,
                        provenance=node.provenance,
                    )
                )
        for dep in svc.get("depends_on") or []:
            dep_name = dep if isinstance(dep, str) else str(dep)
            if dep_name in svc_ids:
                edges.append(
                    NormalizedEdgeV1(
                        from_node_id=node.id,
                        to_node_id=svc_ids[dep_name],
                        kind=GraphEdgeKind.DEPENDS_ON,
                        provenance=node.provenance,
                    )
                )

    graph_hash = hashlib.sha256(content).hexdigest()[:16]
    return NormalizedSystemGraphV1(
        source_model_ids=[source.id],
        nodes=nodes,
        edges=edges,
        graph_hash=graph_hash,
    )


__all__ = ["parse_compose_file", "compose_to_graph", "PARSER_ID"]
