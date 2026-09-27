"""GhostRange Range Compiler (M5)."""

from .pipeline import RangeCompiler, CompilationResult
from .drift import LivingTwinEngine, analyze_revisions
from .intake import RepositoryAcquisitionError, analyze_repository, scan_directory

__all__ = [
    "RangeCompiler",
    "CompilationResult",
    "LivingTwinEngine",
    "analyze_revisions",
    "analyze_repository",
    "scan_directory",
    "RepositoryAcquisitionError",
]
