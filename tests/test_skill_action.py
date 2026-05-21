from __future__ import annotations

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from gemma_cli.cli import cli
from gemma_cli.services import skills as skills_svc
from tests.conftest import MLXStub


def _write_skill(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parse_frontmatter_action_and_input(tmp_home: Path) -> None:
    path = tmp_home / ".config" / "gemma-cli" / "skills" / "c.md"
    _write_skill(
        path,
        "---\nname: c\ndescription: d\naction: git-commit\ninput: staged-diff\n---\n\nbody {{input}}\n",
    )
    skill = skills_svc.find_skill("c")
    assert skill is not None
    assert skill.action == "git-commit"
    assert skill.input_source == "staged-diff"


def test_invalid_action_falls_back_to_print(tmp_home: Path) -> None:
    path = tmp_home / ".config" / "gemma-cli" / "skills" / "x.md"
    _write_skill(path, "---\nname: x\naction: nonsense\n---\nbody")
    skill = skills_svc.find_skill("x")
    assert skill is not None
    assert skill.action == "print"


def test_commit_skill_auto_runs_git_commit(
    tmp_home: Path, tmp_git_repo: Path, monkeypatch, mlx_stub: MLXStub
) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "commit.md",
        "---\nname: commit\ninput: staged-diff\naction: git-commit\n---\n\n{{input}}\n",
    )
    f = tmp_git_repo / "file.txt"
    f.write_text("hello\nworld\n")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_git_repo, check=True)
    monkeypatch.chdir(tmp_git_repo)

    mlx_stub.response = "feat: add world\n"
    runner = CliRunner()
    res = runner.invoke(cli, ["run", "commit"], input="y\n")
    assert res.exit_code == 0, res.output
    log = subprocess.run(["git", "log", "--oneline"], cwd=tmp_git_repo, capture_output=True, text=True)
    assert "add world" in log.stdout


def test_pr_skill_invokes_gh_or_warns_when_missing(
    tmp_home: Path, tmp_git_repo: Path, monkeypatch, mlx_stub: MLXStub
) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "pr.md",
        "---\nname: pr\ninput: branch-diff\naction: gh-pr\nbase: main\n---\n\n{{input}}\n",
    )
    subprocess.run(["git", "checkout", "-q", "-b", "feat"], cwd=tmp_git_repo, check=True)
    f = tmp_git_repo / "file.txt"
    f.write_text("hello\nworld\n")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_git_repo, check=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "commit", "-q", "-m", "wip"], cwd=tmp_git_repo, check=True, env=env)
    monkeypatch.chdir(tmp_git_repo)
    monkeypatch.setattr("shutil.which", lambda _name: None)

    mlx_stub.response = "TITLE: feat: 추가\n---\n## 요약\n- A\n"
    runner = CliRunner()
    res = runner.invoke(cli, ["run", "pr"], input="y\n")
    assert res.exit_code == 0, res.output
    assert "gh" in res.output and "설치" in res.output


def test_staged_diff_input_empty_errors(tmp_home: Path, tmp_git_repo: Path, monkeypatch) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "commit.md",
        "---\nname: commit\ninput: staged-diff\naction: git-commit\n---\n\n{{input}}\n",
    )
    monkeypatch.chdir(tmp_git_repo)
    runner = CliRunner()
    res = runner.invoke(cli, ["run", "commit"])
    assert res.exit_code != 0
    assert "스테이징" in res.output


def test_commit_context_includes_branch_and_log(
    tmp_home: Path, tmp_git_repo: Path, monkeypatch, mlx_stub: MLXStub
) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "commit.md",
        "---\nname: commit\ninput: commit-context\naction: git-commit\n---\n\n{{input}}\n",
    )
    subprocess.run(["git", "checkout", "-q", "-b", "feature/FRONTEND-1234-login"], cwd=tmp_git_repo, check=True)
    f = tmp_git_repo / "file.txt"
    f.write_text("hello\nworld\n")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_git_repo, check=True)
    monkeypatch.chdir(tmp_git_repo)

    mlx_stub.response = "FRONTEND-1234 feat: 월드 추가"
    runner = CliRunner()
    res = runner.invoke(cli, ["run", "commit"], input="y\n")
    assert res.exit_code == 0, res.output
    user_msg = mlx_stub.last_user_content()
    assert "feature/FRONTEND-1234-login" in user_msg
    assert "최근 커밋" in user_msg
    assert "+world" in user_msg
    log = subprocess.run(["git", "log", "--oneline"], cwd=tmp_git_repo, capture_output=True, text=True)
    assert "FRONTEND-1234 feat: 월드 추가" in log.stdout


def test_branch_or_files_uses_branch_diff_in_git_repo(
    tmp_home: Path, tmp_git_repo: Path, monkeypatch, mlx_stub: MLXStub
) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "jira.md",
        "---\nname: jira\ninput: branch-or-files\naction: print\nbase: main\n---\n\n{{input}}\n",
    )
    subprocess.run(["git", "checkout", "-q", "-b", "feature/PROJ-77-flow"], cwd=tmp_git_repo, check=True)
    (tmp_git_repo / "added.txt").write_text("hello\nworld\n")
    subprocess.run(["git", "add", "added.txt"], cwd=tmp_git_repo, check=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "commit", "-q", "-m", "wip"], cwd=tmp_git_repo, check=True, env=env)
    monkeypatch.chdir(tmp_git_repo)

    mlx_stub.response = "ok"
    runner = CliRunner()
    res = runner.invoke(cli, ["run", "jira"])
    assert res.exit_code == 0, res.output
    content = mlx_stub.last_user_content()
    assert "## 커밋 로그" in content
    assert "+world" in content
    assert "git 저장소가 아니어서" not in content


def test_branch_or_files_scans_files_outside_git(
    tmp_home: Path, tmp_path: Path, monkeypatch, mlx_stub: MLXStub
) -> None:
    work = tmp_path / "workspace"
    work.mkdir()
    (work / "main.py").write_text("def add(a, b):\n    return a + b\n")
    (work / "README.md").write_text("# Project\nsmall description\n")
    sub = work / "module"
    sub.mkdir()
    (sub / "util.py").write_text("VALUE = 42\n")
    (sub / "ignore_me").mkdir()
    (sub / "ignore_me" / "x").write_text("x")
    (work / "node_modules").mkdir()
    (work / "node_modules" / "junk.js").write_text("module.exports={};\n")

    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "jira.md",
        "---\nname: jira\ninput: branch-or-files\naction: print\nbase: main\n---\n\n{{input}}\n",
    )
    monkeypatch.chdir(work)

    mlx_stub.response = "ok"
    runner = CliRunner()
    res = runner.invoke(cli, ["run", "jira"])
    assert res.exit_code == 0, res.output
    content = mlx_stub.last_user_content()
    assert "git 저장소가 아니어서" in content
    assert "main.py" in content
    assert "module/util.py" in content
    assert "VALUE = 42" in content
    assert "node_modules" not in content


def test_branch_or_files_empty_dir_errors(tmp_home: Path, tmp_path: Path, monkeypatch) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "jira.md",
        "---\nname: jira\ninput: branch-or-files\naction: print\nbase: main\n---\n\n{{input}}\n",
    )
    monkeypatch.chdir(empty)
    runner = CliRunner()
    res = runner.invoke(cli, ["run", "jira"])
    assert res.exit_code != 0
    assert "분석할 파일" in res.output


def test_current_branch(tmp_git_repo: Path) -> None:
    from gemma_cli.services import git_ops

    subprocess.run(["git", "checkout", "-q", "-b", "feature/API-99-test"], cwd=tmp_git_repo, check=True)
    assert git_ops.current_branch(tmp_git_repo) == "feature/API-99-test"


def test_skills_list_shows_action_and_input(tmp_home: Path) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "c.md",
        "---\nname: c\ndescription: d\naction: git-commit\ninput: staged-diff\n---\nbody",
    )
    runner = CliRunner()
    res = runner.invoke(cli, ["skills"])
    assert res.exit_code == 0
    assert "git-commit" in res.output
    assert "staged-diff" in res.output
