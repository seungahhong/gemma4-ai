from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import respx
from click.testing import CliRunner

from gemma_cli.cli import cli


def _ollama_response(text: str) -> httpx.Response:
    lines = [
        json.dumps({"message": {"role": "assistant", "content": text}, "done": False}),
        json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}),
    ]
    return httpx.Response(200, content=("\n".join(lines) + "\n").encode())


def test_cli_help_lists_six_commands() -> None:
    runner = CliRunner()
    res = runner.invoke(cli, ["--help"])
    assert res.exit_code == 0
    for cmd in ["review", "commit", "pr", "refactor", "analyze", "ask"]:
        assert cmd in res.output


def test_review_file_target(tmp_path: Path) -> None:
    file = tmp_path / "foo.py"
    file.write_text("def add(a, b):\n    return a+b\n")
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response("## 요약\n괜찮습니다."))
        runner = CliRunner()
        res = runner.invoke(cli, ["review", str(file)])
    assert res.exit_code == 0, res.output


def test_review_outside_git_without_target_errors(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    res = runner.invoke(cli, ["review"])
    assert res.exit_code != 0
    assert "git" in res.output


def test_ask_one_shot_writes_session(tmp_home: Path) -> None:
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response("안녕하세요"))
        runner = CliRunner()
        res = runner.invoke(cli, ["ask", "안녕"])
    assert res.exit_code == 0, res.output
    sessions = list((tmp_home / ".local" / "share" / "gemma-cli" / "sessions").glob("*.jsonl"))
    assert len(sessions) == 1
    content = sessions[0].read_text(encoding="utf-8")
    assert "안녕" in content
    assert "안녕하세요" in content


def test_ask_resume_last(tmp_home: Path) -> None:
    sess_dir = tmp_home / ".local" / "share" / "gemma-cli" / "sessions"
    sess_dir.mkdir(parents=True)
    sess_file = sess_dir / "20260101T000000-abcdef.jsonl"
    sess_file.write_text(
        json.dumps({"role": "user", "content": "이전질문"}, ensure_ascii=False) + "\n"
        + json.dumps({"role": "assistant", "content": "이전답변"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response("새답변"))
        runner = CliRunner()
        res = runner.invoke(cli, ["ask", "--resume", "LAST", "새질문"])
    assert res.exit_code == 0, res.output
    text = sess_file.read_text(encoding="utf-8")
    assert "새질문" in text
    assert "새답변" in text


def test_commit_no_staged_returns_message(tmp_git_repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_git_repo)
    runner = CliRunner()
    res = runner.invoke(cli, ["commit"])
    assert res.exit_code == 0
    assert "스테이징" in res.output


def test_commit_with_staged_changes_yes(tmp_git_repo: Path, monkeypatch) -> None:
    import subprocess

    f = tmp_git_repo / "file.txt"
    f.write_text("hello\nworld\n")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_git_repo, check=True)
    monkeypatch.chdir(tmp_git_repo)

    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response("feat: add world\n"))
        runner = CliRunner()
        res = runner.invoke(cli, ["commit"], input="y\n")
    assert res.exit_code == 0, res.output
    log = subprocess.run(["git", "log", "--oneline"], cwd=tmp_git_repo, capture_output=True, text=True)
    assert "add world" in log.stdout


def test_refactor_diff_applied(tmp_git_repo: Path, monkeypatch) -> None:
    target = tmp_git_repo / "file.txt"
    target.write_text("hello\n")
    monkeypatch.chdir(tmp_git_repo)
    diff = (
        f"--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-hello\n+HELLO\n"
    )
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response(diff))
        runner = CliRunner()
        res = runner.invoke(cli, ["refactor", "file.txt"], input="y\n")
    assert res.exit_code == 0, res.output
    assert target.read_text() == "HELLO\n"


def test_refactor_rejected_keeps_file(tmp_git_repo: Path, monkeypatch) -> None:
    target = tmp_git_repo / "file.txt"
    target.write_text("hello\n")
    monkeypatch.chdir(tmp_git_repo)
    diff = "--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-hello\n+HELLO\n"
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response(diff))
        runner = CliRunner()
        res = runner.invoke(cli, ["refactor", "file.txt"], input="n\n")
    assert res.exit_code == 0
    assert target.read_text() == "hello\n"


def test_analyze_directory(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response("## 구조\n분석 결과"))
        runner = CliRunner()
        res = runner.invoke(cli, ["analyze", str(tmp_path)])
    assert res.exit_code == 0, res.output


def test_pr_creates_with_gh_missing(tmp_git_repo: Path, monkeypatch) -> None:
    import subprocess

    (tmp_git_repo / "file.txt").write_text("hello\nworld\n")
    subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=tmp_git_repo, check=True)
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_git_repo, check=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "commit", "-q", "-m", "add world"], cwd=tmp_git_repo, check=True, env=env)
    monkeypatch.chdir(tmp_git_repo)
    monkeypatch.setattr("shutil.which", lambda _name: None)

    output = "TITLE: feat: 추가\n---\n## 요약\n- A\n"
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=_ollama_response(output))
        runner = CliRunner()
        res = runner.invoke(cli, ["pr", "--base", "main"], input="y\n")
    assert res.exit_code == 0, res.output
    assert "gh" in res.output and "설치" in res.output
