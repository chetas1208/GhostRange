"""Hard production boundary — reject forbidden execution patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass

def _line_looks_executable(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if "FORBIDDEN" in line or "DO NOT" in line.upper():
        return False
    return True


FORBIDDEN_PATTERNS = (
    re.compile(r"\bterraform\s+apply\b", re.I),
    re.compile(r"\btofu\s+apply\b", re.I),
    re.compile(r"\bkubectl\s+apply\b", re.I),
    re.compile(r"\bhelm\s+upgrade\b", re.I),
    re.compile(r"https?://[^\s]+/deploy", re.I),
    re.compile(r"\bssh\s+[^\s]+@", re.I),
)

PRODUCTION_MUTATION_ERROR = (
    "GhostGate refuses production mutation. Generate review artifacts only."
)


@dataclass(frozen=True)
class BoundaryViolation:
    pattern: str
    detail: str


class ProductionBoundaryGuard:
    """Scan text/commands for disallowed production operations."""

    @staticmethod
    def scan_text(text: str) -> list[BoundaryViolation]:
        hits: list[BoundaryViolation] = []
        for line in text.splitlines():
            if not _line_looks_executable(line):
                continue
            for pat in FORBIDDEN_PATTERNS:
                if pat.search(line):
                    hits.append(BoundaryViolation(pattern=pat.pattern, detail=PRODUCTION_MUTATION_ERROR))
                    break
        return hits

    @staticmethod
    def assert_review_only(text: str) -> None:
        violations = ProductionBoundaryGuard.scan_text(text)
        if violations:
            raise PermissionError(violations[0].detail)

    @staticmethod
    def block_model_approval(approver_kind: str) -> None:
        if approver_kind.upper() in ("MODEL", "LLM", "AGENT"):
            raise PermissionError("Models cannot create human approval decisions.")


class ProductionExecutionForbidden(Exception):
    """Raised when code paths attempt live production change."""
