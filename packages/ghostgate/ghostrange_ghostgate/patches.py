"""Review-only patch generation (Compose / config). Never apply."""

from __future__ import annotations

from pathlib import Path

from ghostrange_contracts.ghostgate_m11 import ChangeActionKind, ChangeActionV1

from .boundary import ProductionBoundaryGuard


def auth_lab_remediation_actions() -> list[ChangeActionV1]:
    """Canonical M10/M11 auth middleware fix — tested in twin."""
    return [
        ChangeActionV1(
            kind=ChangeActionKind.CONFIG,
            target_path="services/auth/middleware.py",
            description="Reject X-Forwarded-User unless from trusted proxy CIDR",
            before_summary="Trusts X-Forwarded-User header globally",
            after_summary="Allowlist trusted_proxy_cidrs only",
            remediation_ref="Fix-B.2",
        ),
        ChangeActionV1(
            kind=ChangeActionKind.IDENTITY_POLICY,
            target_path="services/auth/trusted_proxies.yaml",
            description="Define trusted reverse proxy CIDRs",
            before_summary="missing",
            after_summary="10.0.0.0/8",
            remediation_ref="Fix-B.2",
        ),
    ]


def generate_compose_env_patch(actions: list[ChangeActionV1]) -> str:
    """Minimal compose override snippet for review (not executed)."""
    lines = [
        "# GhostGate proposed review patch — DO NOT AUTO-APPLY",
        "services:",
        "  auth:",
        "    environment:",
        "      AUTH_TRUST_FORWARDED_USER: \"false\"",
        "      AUTH_TRUSTED_PROXY_CIDRS: \"10.0.0.0/8\"",
    ]
    for a in actions:
        lines.append(f"    # action: {a.kind.value} {a.target_path} — {a.description}")
    text = "\n".join(lines) + "\n"
    ProductionBoundaryGuard.assert_review_only(text)
    return text


def generate_terraform_snippet(actions: list[ChangeActionV1]) -> str:
    text = "\n".join(
        [
            "# GhostGate Terraform HCL review snippet — live apply blocked by policy",
            'variable "auth_trusted_proxy_cidrs" {',
            '  type    = list(string)',
            '  default = ["10.0.0.0/8"]',
            "}",
            "",
        ]
        + [f"# traces: {a.remediation_ref} {a.target_path}" for a in actions]
    )
    ProductionBoundaryGuard.assert_review_only(text)
    return text


def load_compose_if_exists(path: Path | None) -> str:
    if path and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""
