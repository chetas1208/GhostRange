import shutil

import pytest

from ghostrange_range_compiler.intake.github_fetch import (
    RepositoryAcquisitionError,
    clone_public_repo,
    get_commit_sha,
)
from ghostrange_range_compiler.intake.pipeline import analyze_repository


def test_rejects_non_github_host():
    with pytest.raises(RepositoryAcquisitionError, match="public https://github.com"):
        with clone_public_repo("https://gitlab.com/acme/widgets", "main"):
            pass


def test_rejects_ssh_url():
    with pytest.raises(RepositoryAcquisitionError):
        with clone_public_repo("git@github.com:acme/widgets.git", "main"):
            pass


def test_rejects_file_url():
    with pytest.raises(RepositoryAcquisitionError):
        with clone_public_repo("file:///etc/passwd", "main"):
            pass


def test_rejects_malformed_branch_name():
    with pytest.raises(RepositoryAcquisitionError, match="Invalid branch"):
        with clone_public_repo("https://github.com/acme/widgets", "main; rm -rf /"):
            pass


def test_rejects_empty_branch_name():
    with pytest.raises(RepositoryAcquisitionError):
        with clone_public_repo("https://github.com/acme/widgets", ""):
            pass


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_clone_and_scan_real_public_repo_end_to_end():
    """Network-dependent integration test against a small, stable, long-lived
    public repo. Skips (rather than fails) if the sandbox has no network —
    the heuristic-derivation logic itself is proven offline by
    test_repo_scanner.py against fixtures; this test only proves the
    clone -> cleanup -> scan wiring works against a real GitHub repo."""
    try:
        model = analyze_repository("https://github.com/octocat/Hello-World", "master")
    except RepositoryAcquisitionError as exc:
        pytest.skip(f"network/clone unavailable in this sandbox: {exc}")

    assert model.repository_url == "https://github.com/octocat/Hello-World"
    assert model.branch == "master"
    assert model.commit_sha  # HEAD sha was captured
    assert model.summary.files_scanned >= 1
    # The clone directory must not survive after analyze_repository returns.
    assert "ghostrange-repo-scan-" not in str(model)


def test_clone_directory_is_removed_after_context_exit():
    try:
        with clone_public_repo("https://github.com/octocat/Hello-World", "master") as repo_dir:
            assert repo_dir.exists()
            captured = repo_dir
    except RepositoryAcquisitionError as exc:
        pytest.skip(f"network/clone unavailable in this sandbox: {exc}")
    assert not captured.exists()


def test_clone_directory_is_removed_even_on_error():
    captured = {}
    try:
        with clone_public_repo("https://github.com/octocat/Hello-World", "master") as repo_dir:
            captured["path"] = repo_dir
            raise ValueError("simulated failure inside the with-block")
    except RepositoryAcquisitionError as exc:
        pytest.skip(f"network/clone unavailable in this sandbox: {exc}")
    except ValueError:
        pass
    assert "path" in captured
    assert not captured["path"].exists()


def test_get_commit_sha_returns_none_for_non_repo(tmp_path):
    assert get_commit_sha(tmp_path) is None
