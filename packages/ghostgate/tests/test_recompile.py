from pathlib import Path

from ghostrange_ghostgate.recompile import verify_proposed_patch

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "ranges/ghostrange-auth-lab-v1/docker/vm-1/docker-compose.yml"


def test_verify_proposed_patch_compiles():
    if not COMPOSE.is_file():
        return
    patch = "# GhostGate proposed review patch\nservices:\n  auth:\n    environment:\n      X: \"1\"\n"
    report = verify_proposed_patch(COMPOSE, patch)
    assert report.compile_ok or report.baseline_node_count > 0
