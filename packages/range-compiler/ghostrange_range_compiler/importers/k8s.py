"""Kubernetes YAML importer — bounded subset, secret references only."""

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
    GraphNodeKind,
    NormalizedNodeV1,
    NormalizedSystemGraphV1,
    SourceProvenanceV1,
)

PARSER_ID = "ghostrange.importer.k8s"
PARSER_VERSION = "0.1.0"

_SUPPORTED_KINDS = frozenset(
    {"Deployment", "StatefulSet", "Service", "ConfigMap", "Secret", "Ingress", "NetworkPolicy", "PersistentVolumeClaim"}
)


def _documents(path: Path) -> list[dict[str, Any]]:
    content = path.read_text(encoding="utf-8", errors="replace")
    docs = []
    for doc in yaml.safe_load_all(content):
        if isinstance(doc, dict):
            docs.append(doc)
    return docs


def parse_k8s_file(path: Path) -> SourceModelV1:
    content = path.read_bytes()
    resources: list[SourceResourceRecordV1] = []
    warnings: list[SourceWarningV1] = []
    secret_refs: list[str] = []

    for doc in _documents(path):
        kind = doc.get("kind")
        meta = doc.get("metadata") or {}
        name = meta.get("name", "unnamed")
        if kind not in _SUPPORTED_KINDS:
            warnings.append(
                SourceWarningV1(
                    code="UNSUPPORTED_KIND",
                    message=f"Kind {kind} not in M5 v1 subset",
                    source_location=str(path),
                    status=UnsupportedConstructStatus.APPROXIMATED,
                )
            )
            continue
        resources.append(
            SourceResourceRecordV1(
                construct_type=f"k8s.{kind}",
                construct_name=name,
                source_location=f"{path}:{kind}/{name}",
                raw_attributes={"apiVersion": str(doc.get("apiVersion", ""))},
                secret_reference_only=(kind == "Secret"),
            )
        )
        if kind == "Secret":
            secret_refs.append(f"secret/{name}")
        spec = doc.get("spec") or {}
        template = spec.get("template") or {}
        pod_spec = template.get("spec") or {}
        if pod_spec.get("hostNetwork"):
            warnings.append(
                SourceWarningV1(
                    code="K8S_HOST_NETWORK",
                    message=f"{kind}/{name} uses hostNetwork",
                    source_location=str(path),
                    status=UnsupportedConstructStatus.UNSUPPORTED_REQUIRED,
                )
            )
        for c in pod_spec.get("containers") or []:
            if c.get("securityContext", {}).get("privileged"):
                warnings.append(
                    SourceWarningV1(
                        code="K8S_PRIVILEGED",
                        message=f"{kind}/{name} privileged container",
                        source_location=str(path),
                        status=UnsupportedConstructStatus.UNSUPPORTED_REQUIRED,
                    )
                )

    return SourceModelV1(
        source_type=SourceType.KUBERNETES,
        files=[
            SourceFileRefV1(
                path=str(path),
                content_hash=hashlib.sha256(content).hexdigest(),
                byte_size=len(content),
            )
        ],
        resources=resources,
        secrets_references=secret_refs,
        warnings=warnings,
        parser_id=PARSER_ID,
        parser_version=PARSER_VERSION,
    )


def k8s_to_graph(source: SourceModelV1, path: Path) -> NormalizedSystemGraphV1:
    nodes: list[NormalizedNodeV1] = []
    for doc in _documents(path):
        kind = doc.get("kind")
        meta = doc.get("metadata") or {}
        name = meta.get("name", "unnamed")
        if kind not in _SUPPORTED_KINDS:
            continue
        node_kind = GraphNodeKind.SERVICE
        if kind in ("Deployment", "StatefulSet"):
            node_kind = GraphNodeKind.POD
        elif kind == "Service":
            node_kind = GraphNodeKind.SERVICE
        elif kind == "Secret":
            node_kind = GraphNodeKind.SECRET_REFERENCE
        nodes.append(
            NormalizedNodeV1(
                name=f"{kind.lower()}/{name}",
                kind=node_kind,
                provenance=SourceProvenanceV1(
                    source_file=str(path),
                    source_construct=f"{kind}/{name}",
                    source_location=f"{path}:{kind}/{name}",
                    parser_id=PARSER_ID,
                ),
            )
        )
    return NormalizedSystemGraphV1(source_model_ids=[source.id], nodes=nodes, edges=[])


__all__ = ["parse_k8s_file", "k8s_to_graph"]
