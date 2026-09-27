"""GitHub-repo-as-input intake: acquisition + heuristic derivation.

See ``pipeline.analyze_repository`` for the single entry point most callers
want (clone -> scan -> DerivedSystemModelV1). ``repo_scanner.scan_directory``
is exposed separately so tests (and any future non-GitHub source, e.g. an
already-checked-out local path) can drive the heuristics without a network
clone.
"""

from .github_fetch import RepositoryAcquisitionError, clone_public_repo, get_commit_sha
from .pipeline import analyze_repository
from .repo_scanner import scan_directory

__all__ = [
    "analyze_repository",
    "clone_public_repo",
    "get_commit_sha",
    "scan_directory",
    "RepositoryAcquisitionError",
]
