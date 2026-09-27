"""Static checks on generated patches (untrusted until validated)."""

from __future__ import annotations

import re
from dataclasses import dataclass

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----"),
)
UNSAFE_PATTERNS = (
    re.compile(r"privileged:\s*true", re.I),
    re.compile(r"hostNetwork:\s*true", re.I),
    re.compile(r"DROP TABLE", re.I),
)


@dataclass
class PatchSecurityFinding:
    code: str
    detail: str


def scan_patch(patch_text: str) -> list[PatchSecurityFinding]:
    findings: list[PatchSecurityFinding] = []
    for pat in SECRET_PATTERNS:
        if pat.search(patch_text):
            findings.append(PatchSecurityFinding("SECRET_EXPOSURE", "Patch may embed secrets"))
    for pat in UNSAFE_PATTERNS:
        if pat.search(patch_text):
            findings.append(PatchSecurityFinding("UNSAFE_CHANGE", "Patch contains high-risk directive"))
    return findings
