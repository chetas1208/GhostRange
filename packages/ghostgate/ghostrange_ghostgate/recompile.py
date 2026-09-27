"""Exact-patch recompile loop — proposed production patch → Range Compiler → twin verify."""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ghostrange_contracts.ghostgate_m11 import EquivalenceStatus


@dataclass
class PatchRecompileReportV1:
    """M11 blocker closure — local compile verification (not live Vultr)."""

    base_compose_path: str
    patched_compose_digest: str
    baseline_node_count: int
    patched_node_count: int
    compile_ok: bool
    fidelity_sufficient: bool
    equivalence_vs_tested: EquivalenceStatus
    errors: list[str] = field(default_factory=list)
    note: str = "COMPILE_IN_PROCESS — not live Vultr promotion world"


def _merge_compose_patch(base_path: Path, patch_text: str) -> Path:
    merged = base_path.read_text(encoding="utf-8")
    if patch_text.strip():
        merged += "\n# --- GhostGate proposed patch (review only) ---\n"
        merged += patch_text
    tmp = Path(tempfile.mkstemp(suffix="-ghostgate-patched.yml")[1])
    tmp.write_text(merged, encoding="utf-8")
    return tmp


def verify_proposed_patch(
    base_compose_path: Path,
    patch_text: str,
    *,
    tested_node_count: int | None = None,
) -> PatchRecompileReportV1:
    """Run Range Compiler on baseline and patched compose; compare graph shape."""
    from ghostrange_range_compiler.pipeline import RangeCompiler

    errors: list[str] = []
    rc = RangeCompiler()
    if not base_compose_path.is_file():
        return PatchRecompileReportV1(
            base_compose_path=str(base_compose_path),
            patched_compose_digest="",
            baseline_node_count=0,
            patched_node_count=0,
            compile_ok=False,
            fidelity_sufficient=False,
            equivalence_vs_tested=EquivalenceStatus.NOT_COMPARABLE,
            errors=["missing_base_compose"],
        )

    try:
        baseline = rc.compile_compose(base_compose_path)
    except Exception as exc:
        return PatchRecompileReportV1(
            base_compose_path=str(base_compose_path),
            patched_compose_digest="",
            baseline_node_count=0,
            patched_node_count=0,
            compile_ok=False,
            fidelity_sufficient=False,
            equivalence_vs_tested=EquivalenceStatus.UNKNOWN,
            errors=[f"baseline_compile:{exc.__class__.__name__}"],
        )

    baseline_nodes = len(baseline.graph.nodes)
    patched_path = _merge_compose_patch(base_compose_path, patch_text)
    patched_digest = hashlib.sha256(patched_path.read_bytes()).hexdigest()
    try:
        patched = rc.compile_compose(patched_path)
    except Exception as exc:
        errors.append(f"patched_compile:{exc.__class__.__name__}")
        patched_nodes = 0
        compile_ok = False
        fidelity_ok = False
    else:
        patched_nodes = len(patched.graph.nodes)
        compile_ok = not patched.errors
        fidelity_ok = bool(patched.fidelity_report.valid_for_investigation)
        if baseline.errors or patched.errors:
            errors.extend(baseline.errors + patched.errors)

    equiv = EquivalenceStatus.EXACT
    if not compile_ok:
        equiv = EquivalenceStatus.NOT_COMPARABLE
    elif patched_nodes != baseline_nodes:
        equiv = EquivalenceStatus.FUNCTIONALLY_EQUIVALENT
    if tested_node_count is not None and patched_nodes != tested_node_count:
        equiv = EquivalenceStatus.MATERIAL_DIFFERENCE

    try:
        patched_path.unlink(missing_ok=True)
    except OSError:
        pass

    return PatchRecompileReportV1(
        base_compose_path=str(base_compose_path),
        patched_compose_digest=f"sha256:{patched_digest}",
        baseline_node_count=baseline_nodes,
        patched_node_count=patched_nodes,
        compile_ok=compile_ok,
        fidelity_sufficient=fidelity_ok,
        equivalence_vs_tested=equiv,
        errors=errors,
    )
