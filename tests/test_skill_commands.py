from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from gemma_cli.cli import cli
from tests.conftest import MLXStub


def _write_skill(path: Path, *, name: str, description: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n",
        encoding="utf-8",
    )


def _user_content(chat: list) -> str:
    return next(m["content"] for m in chat if m["role"] == "user")


def _clean_cwd(tmp_path: Path, monkeypatch) -> Path:
    """프로젝트의 .gemma/skills를 줍지 않도록 빈 디렉터리로 이동한다."""
    clean = tmp_path / "clean"
    clean.mkdir()
    monkeypatch.chdir(clean)
    return clean


def test_skill_appears_in_help(tmp_home: Path, tmp_path: Path, monkeypatch) -> None:
    _clean_cwd(tmp_path, monkeypatch)
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "deploy.md",
        name="deploy", description="배포 체크리스트 생성", body="{{input}}",
    )
    runner = CliRunner()
    res = runner.invoke(cli, ["--help"])
    assert res.exit_code == 0, res.output
    assert "deploy" in res.output
    assert "[스킬]" in res.output
    assert "배포 체크리스트 생성" in res.output


def test_skill_runs_as_first_class_command(
    tmp_home: Path, tmp_path: Path, monkeypatch, mlx_stub: MLXStub
) -> None:
    _clean_cwd(tmp_path, monkeypatch)
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "trans.md",
        name="trans", description="번역", body="언어={{lang}} 원문={{input}}",
    )
    mlx_stub.response = "done"
    runner = CliRunner()
    # `gemma trans ...` — run 없이 직접 호출
    res = runner.invoke(cli, ["trans", "--input", "안녕", "--arg", "lang=en"])
    assert res.exit_code == 0, res.output
    assert mlx_stub.called
    assert mlx_stub.last_user_content() == "언어=en 원문=안녕"


def test_first_class_matches_run(
    tmp_home: Path, tmp_path: Path, monkeypatch, mlx_stub: MLXStub
) -> None:
    """`gemma <skill>`와 `gemma run <skill>`는 동일한 user 메시지를 만든다."""
    _clean_cwd(tmp_path, monkeypatch)
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "echo.md",
        name="echo", description="에코", body="본문={{input}}",
    )
    mlx_stub.response = "ok"
    runner = CliRunner()
    r1 = runner.invoke(cli, ["echo", "--input", "x"])
    r2 = runner.invoke(cli, ["run", "echo", "--input", "x"])
    assert r1.exit_code == 0 and r2.exit_code == 0, (r1.output, r2.output)
    contents = [_user_content(c) for c in mlx_stub.calls]
    assert contents[0] == contents[1] == "본문=x"


def test_builtin_takes_precedence_over_skill(tmp_home: Path, tmp_path: Path, monkeypatch) -> None:
    _clean_cwd(tmp_path, monkeypatch)
    # 빌트인과 동명의 스킬을 만들어도 `gemma commit`은 빌트인이어야 한다.
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "commit.md",
        name="commit", description="스킬쪽 커밋", body="{{input}}",
    )
    runner = CliRunner()
    res = runner.invoke(cli, ["commit", "--help"])
    assert res.exit_code == 0, res.output
    # 빌트인 commit 의 도움말이 나와야 하며, 스킬 표식은 없어야 한다.
    assert "스테이징된 변경사항으로 커밋 메시지를 생성" in res.output
    assert "[사용자 정의 스킬]" not in res.output


def test_unknown_command_errors(tmp_home: Path, tmp_path: Path, monkeypatch) -> None:
    _clean_cwd(tmp_path, monkeypatch)
    runner = CliRunner()
    res = runner.invoke(cli, ["definitely-not-a-skill"])
    assert res.exit_code != 0


def test_project_skill_becomes_command(
    tmp_home: Path, tmp_path: Path, monkeypatch, mlx_stub: MLXStub
) -> None:
    """.gemma/skills 에 떨어뜨린 .md 가 그 디렉터리에서 즉시 커맨드가 된다."""
    project = tmp_path / "proj"
    (project / ".gemma" / "skills").mkdir(parents=True)
    _write_skill(
        project / ".gemma" / "skills" / "jira.md",
        name="jira", description="지라 본문", body="ISSUE: {{input}}",
    )
    monkeypatch.chdir(project)
    mlx_stub.response = "ok"
    runner = CliRunner()
    res = runner.invoke(cli, ["jira", "--input", "로그인 개선"])
    assert res.exit_code == 0, res.output
    assert mlx_stub.called
    assert mlx_stub.last_user_content() == "ISSUE: 로그인 개선"
