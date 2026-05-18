from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import httpx
import respx
from click.testing import CliRunner

from gemma_cli.cli import cli
from gemma_cli.services import skills as skills_svc


def _ollama_response(text: str) -> httpx.Response:
    lines = [
        json.dumps({"message": {"role": "assistant", "content": text}, "done": False}),
        json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}),
    ]
    return httpx.Response(200, content=("\n".join(lines) + "\n").encode())


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


def test_commit_skill_auto_runs_git_commit(tmp_home: Path, tmp_git_repo: Path, monkeypatch) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "commit.md",
        "---\nname: commit\ninput: staged-diff\naction: git-commit\n---\n\n{{input}}\n",
    )
    f = tmp_git_repo / "file.txt"
    f.write_text("hello\nworld\n")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_git_repo, check=True)
    monkeypatch.chdir(tmp_git_repo)

    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response("feat: add world\n"))
        runner = CliRunner()
        res = runner.invoke(cli, ["run", "commit"], input="y\n")
    assert res.exit_code == 0, res.output
    log = subprocess.run(["git", "log", "--oneline"], cwd=tmp_git_repo, capture_output=True, text=True)
    assert "add world" in log.stdout


def test_pr_skill_invokes_gh_or_warns_when_missing(tmp_home: Path, tmp_git_repo: Path, monkeypatch) -> None:
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

    pr_out = "TITLE: feat: 추가\n---\n## 요약\n- A\n"
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response(pr_out))
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


def test_commit_context_includes_branch_and_log(tmp_home: Path, tmp_git_repo: Path, monkeypatch) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "commit.md",
        "---\nname: commit\ninput: commit-context\naction: git-commit\n---\n\n{{input}}\n",
    )
    subprocess.run(["git", "checkout", "-q", "-b", "feature/FRONTEND-1234-login"], cwd=tmp_git_repo, check=True)
    f = tmp_git_repo / "file.txt"
    f.write_text("hello\nworld\n")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_git_repo, check=True)
    monkeypatch.chdir(tmp_git_repo)

    captured_user_msg: dict[str, str] = {}

    def _capture(request):
        payload = json.loads(request.content.decode())
        captured_user_msg["content"] = next(
            m["content"] for m in payload["messages"] if m["role"] == "user"
        )
        return _ollama_response("FRONTEND-1234 feat: 월드 추가")

    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(side_effect=_capture)
        runner = CliRunner()
        res = runner.invoke(cli, ["run", "commit"], input="y\n")
    assert res.exit_code == 0, res.output
    assert "feature/FRONTEND-1234-login" in captured_user_msg["content"]
    assert "최근 커밋" in captured_user_msg["content"]
    assert "+world" in captured_user_msg["content"]
    log = subprocess.run(["git", "log", "--oneline"], cwd=tmp_git_repo, capture_output=True, text=True)
    assert "FRONTEND-1234 feat: 월드 추가" in log.stdout


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
