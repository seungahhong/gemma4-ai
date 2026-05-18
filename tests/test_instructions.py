from __future__ import annotations

from pathlib import Path

from gemma_cli.services.instructions import find_instructions, load_instructions, with_instructions


def test_find_missing(tmp_path: Path) -> None:
    assert find_instructions(tmp_path) is None
    assert load_instructions(tmp_path) == ""


def test_find_in_current_dir(tmp_path: Path) -> None:
    (tmp_path / "GEMMA.md").write_text("프로젝트 룰: 한국어로만 답한다.\n", encoding="utf-8")
    found = find_instructions(tmp_path)
    assert found is not None
    assert found.name == "GEMMA.md"
    assert "한국어로만" in load_instructions(tmp_path)


def test_find_walks_up_tree(tmp_path: Path) -> None:
    (tmp_path / "GEMMA.md").write_text("루트 규칙", encoding="utf-8")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_instructions(nested) == tmp_path / "GEMMA.md"


def test_lowercase_gemma_md(tmp_path: Path) -> None:
    (tmp_path / "gemma.md").write_text("소문자 버전", encoding="utf-8")
    assert find_instructions(tmp_path) is not None


def test_with_instructions_prepends(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "GEMMA.md").write_text("절대 영어로 답하지 마라.", encoding="utf-8")
    merged = with_instructions("기본 시스템 프롬프트")
    assert "기본 시스템 프롬프트" in merged
    assert "절대 영어로 답하지 마라." in merged
    assert "프로젝트 지침" in merged


def test_with_instructions_passthrough_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert with_instructions("base") == "base"
