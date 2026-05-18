from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def _run(args: list[str], cwd: Path | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def is_repo(cwd: Path | None = None) -> bool:
    res = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd)
    return res.returncode == 0 and res.stdout.strip() == "true"


def staged_diff(cwd: Path | None = None) -> str:
    res = _run(["git", "diff", "--staged"], cwd=cwd)
    if res.returncode != 0:
        raise GitError(res.stderr.strip() or "git diff --staged 실패")
    return res.stdout


def unstaged_diff(cwd: Path | None = None) -> str:
    res = _run(["git", "diff"], cwd=cwd)
    if res.returncode != 0:
        raise GitError(res.stderr.strip() or "git diff 실패")
    return res.stdout


def recent_log(n: int = 20, cwd: Path | None = None) -> str:
    res = _run(["git", "log", f"-n{n}", "--oneline"], cwd=cwd)
    if res.returncode != 0:
        raise GitError(res.stderr.strip() or "git log 실패")
    return res.stdout


def current_branch(cwd: Path | None = None) -> str:
    res = _run(["git", "branch", "--show-current"], cwd=cwd)
    if res.returncode != 0:
        return ""
    return res.stdout.strip()


def branch_diff(base: str, cwd: Path | None = None) -> str:
    res = _run(["git", "diff", f"{base}...HEAD"], cwd=cwd)
    if res.returncode != 0:
        raise GitError(res.stderr.strip() or f"git diff {base}...HEAD 실패")
    return res.stdout


def branch_log(base: str, cwd: Path | None = None) -> str:
    res = _run(["git", "log", f"{base}..HEAD", "--oneline"], cwd=cwd)
    if res.returncode != 0:
        raise GitError(res.stderr.strip() or f"git log {base}..HEAD 실패")
    return res.stdout


def commit(message: str, cwd: Path | None = None) -> None:
    res = _run(["git", "commit", "-m", message], cwd=cwd)
    if res.returncode != 0:
        raise GitError(res.stderr.strip() or "git commit 실패")


def apply_patch(diff: str, cwd: Path | None = None) -> None:
    res = _run(["git", "apply", "-"], cwd=cwd, input_text=diff)
    if res.returncode != 0:
        raise GitError(res.stderr.strip() or "git apply 실패")
