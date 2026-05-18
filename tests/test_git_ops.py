from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from gemma_cli.services import git_ops


def test_is_repo_outside(tmp_path: Path) -> None:
    assert git_ops.is_repo(tmp_path) is False


def test_staged_and_unstaged_diff(tmp_git_repo: Path) -> None:
    f = tmp_git_repo / "file.txt"
    f.write_text("hello\nworld\n")

    unstaged = git_ops.unstaged_diff(tmp_git_repo)
    assert "+world" in unstaged

    subprocess.run(["git", "add", "file.txt"], cwd=tmp_git_repo, check=True)
    staged = git_ops.staged_diff(tmp_git_repo)
    assert "+world" in staged


def test_recent_log(tmp_git_repo: Path) -> None:
    log = git_ops.recent_log(5, tmp_git_repo)
    assert "init" in log


def test_apply_patch(tmp_git_repo: Path) -> None:
    f = tmp_git_repo / "file.txt"
    original = f.read_text()
    new = original + "added\n"
    diff = subprocess.run(
        ["git", "diff", "--no-index", "--", "file.txt", "-"],
        cwd=tmp_git_repo,
        input=new,
        capture_output=True,
        text=True,
    )
    patch = diff.stdout.replace("--- a/file.txt", "--- a/file.txt").replace("+++ b/-", "+++ b/file.txt")
    git_ops.apply_patch(patch, tmp_git_repo)
    assert (tmp_git_repo / "file.txt").read_text().endswith("added\n")


def test_commit_creates_commit(tmp_git_repo: Path) -> None:
    f = tmp_git_repo / "file.txt"
    f.write_text("hello\nworld\n")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_git_repo, check=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_git_repo)
        git_ops.commit("feat: add world")
    finally:
        os.chdir(old_cwd)
    log = subprocess.run(["git", "log", "--oneline"], cwd=tmp_git_repo, capture_output=True, text=True, env=env)
    assert "add world" in log.stdout


def test_apply_patch_invalid_raises(tmp_git_repo: Path) -> None:
    with pytest.raises(git_ops.GitError):
        git_ops.apply_patch("not a real diff", tmp_git_repo)
