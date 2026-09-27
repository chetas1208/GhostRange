"""Production runtime must not depend on evaluation/private hidden bundles."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FORBIDDEN_IMPORT_FRAGMENTS = (
    "evaluation.private",
    "ArenaHiddenStore",
    "ghostrange_ghostarena.hidden_store",
)


def _python_files_under(*roots: str) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        base = REPO / root
        if not base.exists():
            continue
        out.extend(base.rglob("*.py"))
    return out


def test_apps_api_does_not_import_hidden_store():
    offenders: list[str] = []
    for path in _python_files_under("apps/api"):
        text = path.read_text(encoding="utf-8")
        for frag in FORBIDDEN_IMPORT_FRAGMENTS:
            if frag in text:
                offenders.append(f"{path.relative_to(REPO)}: {frag}")
    assert not offenders, offenders


def test_ghostevolve_does_not_import_hidden_store():
    for path in _python_files_under("packages/ghostevolve"):
        text = path.read_text(encoding="utf-8")
        assert "ArenaHiddenStore" not in text
        assert "evaluation/private" not in text
