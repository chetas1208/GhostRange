"""Public GitHub repository acquisition — shallow clone into a temp directory.

Scope (explicit — see ``docs/architecture/RANGE_COMPILER.md`` and this
package's README): PUBLIC repositories only. There is no GitHub App /
OAuth / token-based private-repo access here — that integration is
deferred to a later pass.

Safety notes:
- Only ``https://github.com/<owner>/<repo>`` URLs are accepted this pass;
  anything else (other hosts, ``git@`` SSH URLs, ``file://``, etc.) is
  rejected before a subprocess is ever spawned.
- ``branch`` is validated against a strict allow-list of characters before
  being passed as a ``git`` argument (argv, never a shell string — but
  validated anyway as defense in depth).
- The clone is always removed on exit, even if the caller raises.
- Cloned bytes are only ever read (by ``repo_scanner``) — never executed,
  imported, or ``eval``'d.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_ALLOWED_URL_RE = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?/?$"
)
_BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,255}$")


class RepositoryAcquisitionError(RuntimeError):
    """Raised when a repository cannot be safely or successfully cloned."""


def _validate_inputs(repository_url: str, branch: str) -> None:
    if not _ALLOWED_URL_RE.match(repository_url.strip()):
        raise RepositoryAcquisitionError(
            "Only public https://github.com/<owner>/<repo> URLs are supported in "
            f"this pass (private-repo/GitHub-App auth is deferred), got: {repository_url!r}"
        )
    if not branch or not _BRANCH_RE.match(branch):
        raise RepositoryAcquisitionError(f"Invalid branch name: {branch!r}")


@contextmanager
def clone_public_repo(
    repository_url: str, branch: str = "main", *, timeout_seconds: int = 60
) -> Iterator[Path]:
    """Shallow-clone a public GitHub repo into a temp dir; yield its path.

    The directory (including ``.git`` metadata) is always removed when the
    ``with`` block exits, including on error. A private repo or a bad
    branch name simply fails the clone with a clear ``RepositoryAcquisitionError``
    — no credentials are ever read, stored, or prompted for
    (``GIT_TERMINAL_PROMPT=0``).
    """
    _validate_inputs(repository_url, branch)
    tmp_dir = tempfile.mkdtemp(prefix="ghostrange-repo-scan-")
    try:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    branch,
                    "--single-branch",
                    "--no-tags",
                    repository_url,
                    tmp_dir,
                ],
                check=True,
                capture_output=True,
                timeout=timeout_seconds,
                env=env,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            raise RepositoryAcquisitionError(
                f"git clone failed for {repository_url}@{branch}: {stderr.strip() or exc}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RepositoryAcquisitionError(
                f"git clone timed out after {timeout_seconds}s for {repository_url}@{branch}"
            ) from exc
        except FileNotFoundError as exc:
            raise RepositoryAcquisitionError("git executable not found on PATH") from exc
        yield Path(tmp_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def get_commit_sha(repo_dir: Path) -> str | None:
    """Best-effort HEAD sha of a cloned repo; ``None`` if it cannot be read."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return result.stdout.decode("utf-8", errors="replace").strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None


__all__ = ["clone_public_repo", "get_commit_sha", "RepositoryAcquisitionError"]
