"""GhostMesh — federated knowledge artifacts with local-first validation."""

from .harness import GhostMeshHarness, run_m13_demo_story
from .mesh import GhostMeshNode

__all__ = ["GhostMeshNode", "GhostMeshHarness", "run_m13_demo_story"]
