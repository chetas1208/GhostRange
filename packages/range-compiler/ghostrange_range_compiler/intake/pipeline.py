"""End-to-end entry point: public GitHub repo URL + branch -> DerivedSystemModelV1.

Combines :mod:`github_fetch` (acquisition) and :mod:`repo_scanner`
(heuristic analysis). This is the function the API layer calls; it is
deliberately synchronous (shells out to ``git`` and does blocking file
I/O) — callers on an event loop should run it in a thread pool (FastAPI's
sync ``def`` route handlers do this automatically).
"""

from __future__ import annotations

from ghostrange_contracts.derived_system_model import DerivedSystemModelV1

from .github_fetch import clone_public_repo, get_commit_sha
from .repo_scanner import scan_directory


def analyze_repository(
    repository_url: str, branch: str = "main", *, timeout_seconds: int = 60
) -> DerivedSystemModelV1:
    """Clone ``repository_url`` at ``branch`` (public repos only), scan it,
    and return a :class:`DerivedSystemModelV1`. The clone is always cleaned
    up before this function returns, success or failure."""
    with clone_public_repo(repository_url, branch, timeout_seconds=timeout_seconds) as repo_dir:
        commit_sha = get_commit_sha(repo_dir)
        model = scan_directory(repo_dir, repository_url=repository_url, branch=branch)
        return model.model_copy(update={"commit_sha": commit_sha})


__all__ = ["analyze_repository"]
