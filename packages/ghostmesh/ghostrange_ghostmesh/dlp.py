"""Contribution DLP — direct identifiers and secrets must not cross Mesh."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("bearer", re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.I)),
    ("hostname", re.compile(r"\b[a-z0-9][a-z0-9-]{1,62}\.(?:internal|local|corp|prod)\b", re.I)),
    ("url_path", re.compile(r"/internal/[a-z0-9/_-]+", re.I)),
    ("cloud_id", re.compile(r"\b(i-[a-f0-9]{8,}|projects/[a-z0-9-]+)\b", re.I)),
]

EXECUTION_SMUGGLE = re.compile(
    r"\b(RUN_COMMAND|CREATE_WORLD|DEPLOY|ROLLBACK|EXECUTE_ATTACK|kubectl|terraform_apply|ssh\s)\b",
    re.I,
)


@dataclass
class DLPFinding:
    kind: str
    snippet: str


@dataclass
class DLPReport:
    ok: bool
    findings: list[DLPFinding] = field(default_factory=list)


def scan_text(text: str) -> DLPReport:
    findings: list[DLPFinding] = []
    for kind, pat in FORBIDDEN_PATTERNS:
        m = pat.search(text)
        if m:
            findings.append(DLPFinding(kind=kind, snippet=m.group(0)[:80]))
    if EXECUTION_SMUGGLE.search(text):
        findings.append(DLPFinding(kind="execution_smuggle", snippet="execution keyword"))
    return DLPReport(ok=len(findings) == 0, findings=findings)


def scan_contribution_payload(payload: dict) -> DLPReport:
    import json

    return scan_text(json.dumps(payload, sort_keys=True))
