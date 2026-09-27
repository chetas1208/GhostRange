"""Terraform / OpenTofu HCL importer — python-hcl2 only."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import hcl2

from ghostrange_contracts.source_model import (
    SourceFileRefV1,
    SourceModelV1,
    SourceResourceRecordV1,
    SourceType,
    SourceWarningV1,
    UnsupportedConstructStatus,
)

PARSER_ID = "ghostrange.importer.terraform"
PARSER_VERSION = "0.1.0"

_VULTR_RESOURCE_PREFIXES = ("vultr_instance", "vultr_vpc", "vultr_firewall")


def parse_terraform_file(path: Path) -> SourceModelV1:
    content = path.read_bytes()
    text = content.decode("utf-8", errors="replace")
    try:
        parsed = hcl2.loads(text)
    except Exception as exc:  # noqa: BLE001 — surface as warning
        return SourceModelV1(
            source_type=SourceType.TERRAFORM,
            files=[
                SourceFileRefV1(
                    path=str(path),
                    content_hash=hashlib.sha256(content).hexdigest(),
                    byte_size=len(content),
                )
            ],
            warnings=[
                SourceWarningV1(
                    code="HCL_PARSE_ERROR",
                    message=str(exc),
                    source_location=str(path),
                    status=UnsupportedConstructStatus.UNSUPPORTED_REQUIRED,
                )
            ],
            parser_id=PARSER_ID,
            parser_version=PARSER_VERSION,
        )

    resources: list[SourceResourceRecordV1] = []
    warnings: list[SourceWarningV1] = []
    variables: dict[str, str] = {}

    if isinstance(parsed, dict):
        for block_type, blocks in parsed.items():
            if block_type == "resource" and isinstance(blocks, list):
                for res_block in blocks:
                    if not isinstance(res_block, dict):
                        continue
                    for rtype, instances in res_block.items():
                        if not isinstance(instances, list):
                            continue
                        for inst in instances:
                            if not isinstance(inst, dict):
                                continue
                            for rname, attrs in inst.items():
                                resources.append(
                                    SourceResourceRecordV1(
                                        construct_type=f"terraform.resource.{rtype}",
                                        construct_name=rname,
                                        source_location=f"{path}:resource.{rtype}.{rname}",
                                        raw_attributes={
                                            k: str(v)[:200]
                                            for k, v in (attrs or {}).items()
                                            if k != "user_data"
                                        },
                                    )
                                )
                                if rtype.startswith("vultr_"):
                                    pass
                                elif "provisioner" in str(attrs):
                                    warnings.append(
                                        SourceWarningV1(
                                            code="PROVISIONER_PRESENT",
                                            message=f"Resource {rtype}.{rname} may contain provisioners — not executed",
                                            source_location=str(path),
                                            status=UnsupportedConstructStatus.IGNORED_OPTIONAL,
                                        )
                                    )
            elif block_type == "variable" and isinstance(blocks, dict):
                for vname in blocks:
                    variables[vname] = "declared"

    return SourceModelV1(
        source_type=SourceType.TERRAFORM,
        files=[
            SourceFileRefV1(
                path=str(path),
                content_hash=hashlib.sha256(content).hexdigest(),
                byte_size=len(content),
            )
        ],
        resources=resources,
        variables=variables,
        warnings=warnings,
        parser_id=PARSER_ID,
        parser_version=PARSER_VERSION,
    )


def terraform_to_graph(source: SourceModelV1) -> "NormalizedSystemGraphV1":
    from ghostrange_contracts.system_graph import (
        GraphNodeKind,
        NormalizedNodeV1,
        NormalizedSystemGraphV1,
        SourceProvenanceV1,
    )

    nodes: list[NormalizedNodeV1] = []
    for res in source.resources:
        kind = GraphNodeKind.VM if "instance" in res.construct_type else GraphNodeKind.HOST
        nodes.append(
            NormalizedNodeV1(
                name=res.construct_name,
                kind=kind,
                provenance=SourceProvenanceV1(
                    source_file=res.source_location.split(":")[0],
                    source_construct=res.construct_type,
                    source_location=res.source_location,
                    parser_id=PARSER_ID,
                ),
            )
        )
    return NormalizedSystemGraphV1(source_model_ids=[source.id], nodes=nodes, edges=[])


__all__ = ["parse_terraform_file", "terraform_to_graph"]
