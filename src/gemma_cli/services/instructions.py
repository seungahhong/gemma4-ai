from __future__ import annotations

from pathlib import Path

INSTRUCTION_FILENAMES = ("GEMMA.md", "gemma.md")


def find_instructions(start: Path | None = None) -> Path | None:
    """현재 디렉터리부터 부모 트리를 거슬러 올라가며 GEMMA.md를 찾는다."""
    cur = (start or Path.cwd()).resolve()
    for d in [cur, *cur.parents]:
        for name in INSTRUCTION_FILENAMES:
            candidate = d / name
            if candidate.is_file():
                return candidate
    return None


def load_instructions(start: Path | None = None) -> str:
    path = find_instructions(start)
    if not path:
        return ""
    return path.read_text(encoding="utf-8").strip()


def with_instructions(system_prompt: str, *, start: Path | None = None) -> str:
    extra = load_instructions(start)
    if not extra:
        return system_prompt
    return f"{system_prompt}\n\n# 프로젝트 지침 ({find_instructions(start)})\n\n{extra}"
