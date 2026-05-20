from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx
from click.testing import CliRunner

from gemma_cli.cli import cli
from gemma_cli.services import skills as skills_svc


def _write_skill(path: Path, *, name: str, description: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n",
        encoding="utf-8",
    )


def _ollama_response(text: str) -> httpx.Response:
    lines = [
        json.dumps({"message": {"role": "assistant", "content": text}, "done": False}),
        json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}),
    ]
    return httpx.Response(200, content=("\n".join(lines) + "\n").encode())


def test_discover_user_skill(tmp_home: Path) -> None:
    skill_path = tmp_home / ".config" / "gemma-cli" / "skills" / "tdd.md"
    _write_skill(skill_path, name="tdd", description="TDD 검토", body="입력: {{input}}")
    found = skills_svc.discover_skills()
    assert "tdd" in found
    assert found["tdd"].description == "TDD 검토"


def test_project_skill_overrides_user(tmp_home: Path, tmp_path: Path, monkeypatch) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "review.md",
        name="review", description="사용자 버전", body="USER",
    )
    project = tmp_path / "proj"
    project.mkdir()
    _write_skill(
        project / ".gemma" / "skills" / "review.md",
        name="review", description="프로젝트 버전", body="PROJ",
    )
    monkeypatch.chdir(project)
    found = skills_svc.discover_skills()
    assert found["review"].description == "프로젝트 버전"
    assert "PROJ" in found["review"].body


def test_discovery_skips_dangling_symlink(tmp_home: Path) -> None:
    # 읽을 수 없는 파일(끊긴 심볼릭 링크) 하나가 전체 디스커버리를 깨면 안 된다.
    skill_dir = tmp_home / ".config" / "gemma-cli" / "skills"
    _write_skill(skill_dir / "ok.md", name="ok", description="정상", body="{{input}}")
    dangling = skill_dir / "broken.md"
    dangling.symlink_to(skill_dir / "does-not-exist.md")
    found = skills_svc.discover_skills()  # 예외 없이 동작해야 한다
    assert "ok" in found
    assert "broken" not in found


def test_skill_render_substitutes_input_and_args(tmp_home: Path) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "x.md",
        name="x", description="d", body="lang={{lang}} body={{input}}",
    )
    skill = skills_svc.find_skill("x")
    assert skill is not None
    rendered = skill.render(input_text="hello", args={"lang": "ko"})
    assert rendered == "lang=ko body=hello"


def test_skill_without_frontmatter(tmp_home: Path) -> None:
    path = tmp_home / ".config" / "gemma-cli" / "skills" / "plain.md"
    path.parent.mkdir(parents=True)
    path.write_text("그냥 본문만 있음 {{input}}", encoding="utf-8")
    skill = skills_svc.find_skill("plain")
    assert skill is not None
    assert skill.name == "plain"
    assert skill.description == ""


def test_skills_list_command_empty(tmp_home: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    res = runner.invoke(cli, ["skills"])
    assert res.exit_code == 0
    assert "등록된 스킬이 없습니다" in res.output


def test_skills_list_command_shows_registered(tmp_home: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "lint.md",
        name="lint", description="린트 검사", body="{{input}}",
    )
    runner = CliRunner()
    res = runner.invoke(cli, ["skills"])
    assert res.exit_code == 0
    assert "lint" in res.output
    assert "린트 검사" in res.output


def test_run_unknown_skill_errors(tmp_home: Path) -> None:
    runner = CliRunner()
    res = runner.invoke(cli, ["run", "missing"])
    assert res.exit_code != 0
    assert "찾을 수 없습니다" in res.output


def test_run_skill_with_file_input(tmp_home: Path, tmp_path: Path) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "summarize.md",
        name="summarize", description="요약", body="다음을 요약: {{input}}",
    )
    file = tmp_path / "doc.txt"
    file.write_text("긴 문서 내용", encoding="utf-8")
    with respx.mock(base_url="http://localhost:11434") as mock:
        route = mock.post("/api/chat").mock(return_value=_ollama_response("요약 결과"))
        runner = CliRunner()
        res = runner.invoke(cli, ["run", "summarize", str(file)])
    assert res.exit_code == 0, res.output
    assert route.called
    payload = json.loads(route.calls[0].request.content.decode())
    user_msg = next(m for m in payload["messages"] if m["role"] == "user")
    assert "긴 문서 내용" in user_msg["content"]
    assert "다음을 요약" in user_msg["content"]


def test_run_skill_with_inline_input_and_args(tmp_home: Path) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "trans.md",
        name="trans", description="번역", body="언어={{lang}} 원문={{input}}",
    )
    with respx.mock(base_url="http://localhost:11434") as mock:
        route = mock.post("/api/chat").mock(return_value=_ollama_response("done"))
        runner = CliRunner()
        res = runner.invoke(
            cli,
            ["run", "trans", "--input", "안녕", "--arg", "lang=en"],
        )
    assert res.exit_code == 0, res.output
    payload = json.loads(route.calls[0].request.content.decode())
    user_msg = next(m for m in payload["messages"] if m["role"] == "user")
    assert user_msg["content"] == "언어=en 원문=안녕"


def test_gemma_md_prepended_to_system_prompt(tmp_home: Path, tmp_path: Path, monkeypatch) -> None:
    _write_skill(
        tmp_home / ".config" / "gemma-cli" / "skills" / "h.md",
        name="h", description="h", body="say {{input}}",
    )
    (tmp_path / "GEMMA.md").write_text("출력은 반드시 이모지 포함.", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with respx.mock(base_url="http://localhost:11434") as mock:
        route = mock.post("/api/chat").mock(return_value=_ollama_response("ok"))
        runner = CliRunner()
        res = runner.invoke(cli, ["run", "h", "--input", "hi"])
    assert res.exit_code == 0, res.output
    payload = json.loads(route.calls[0].request.content.decode())
    system_msg = next(m for m in payload["messages"] if m["role"] == "system")
    assert "출력은 반드시 이모지 포함." in system_msg["content"]
    assert "프로젝트 지침" in system_msg["content"]
