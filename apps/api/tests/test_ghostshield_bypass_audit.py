"""Static audit: RealVultrProvider / create_compute only in allowlisted modules."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

ALLOWLIST = {
    REPO / "apps/api/ghostrange_api/compute_provider.py",
    REPO / "packages/range-runtime/ghostrange_range_runtime/vultr_adapter.py",
    REPO / "packages/vultr-control/ghostrange_vultr_control/real_provider.py",
    REPO / "packages/vultr-control/ghostrange_vultr_control/mock_provider.py",
}

FORBIDDEN_SNIPPETS = ("RealVultrProvider(", "from ghostrange_vultr_control import RealVultrProvider")


# Documented BYPASSABLE until golden-path + dry-check route through gateway (M17 Wave 2).
KNOWN_API_BYPASS = frozenset(
    {
        "orchestrator.py",
        "scheduler_routes.py",
    }
)


def test_no_new_real_vultr_imports_in_api():
    api_root = REPO / "apps/api/ghostrange_api"
    violations: list[str] = []
    for path in api_root.rglob("*.py"):
        if path.name == "compute_provider.py" or path.name in KNOWN_API_BYPASS:
            continue
        text = path.read_text(encoding="utf-8")
        if "RealVultrProvider" in text:
            violations.append(str(path.relative_to(REPO)))
    assert not violations, f"New RealVultrProvider import outside allowlist: {violations}"
