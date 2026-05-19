from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


VALID_ACTIONS = {"print", "git-commit", "gh-pr"}
VALID_INPUTS = {"manual", "staged-diff", "branch-diff", "commit-context", "branch-or-files"}


@dataclass
class Skill:
    name: str
    description: str
    body: str
    source: Path
    action: str = "print"
    input_source: str = "manual"
    base: str = "main"

    def render(self, *, input_text: str = "", args: dict[str, str] | None = None) -> str:
        text = self.body.replace("{{input}}", input_text)
        if args:
            for k, v in args.items():
                text = text.replace(f"{{{{{k}}}}}", v)
        return text


def _user_skill_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "gemma-cli" / "skills"


def _project_skill_dir(start: Path | None = None) -> Path | None:
    cur = (start or Path.cwd()).resolve()
    for d in [cur, *cur.parents]:
        candidate = d / ".gemma" / "skills"
        if candidate.is_dir():
            return candidate
    return None


def _parse_skill(path: Path) -> Skill | None:
    text = path.read_text(encoding="utf-8")
    name = path.stem
    description = ""
    action = "print"
    input_source = "manual"
    base = "main"
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            header = text[4:end]
            body = text[end + 4 :].lstrip("\n")
            try:
                meta = yaml.safe_load(header) or {}
                if isinstance(meta, dict):
                    name = str(meta.get("name", name))
                    description = str(meta.get("description", ""))
                    action = str(meta.get("action", action))
                    input_source = str(meta.get("input", input_source))
                    base = str(meta.get("base", base))
            except yaml.YAMLError:
                pass
    if action not in VALID_ACTIONS:
        action = "print"
    if input_source not in VALID_INPUTS:
        input_source = "manual"
    return Skill(
        name=name,
        description=description,
        body=body.rstrip(),
        source=path,
        action=action,
        input_source=input_source,
        base=base,
    )


def discover_skills(start: Path | None = None) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    for d in (_user_skill_dir(), _project_skill_dir(start)):
        if not d or not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            skill = _parse_skill(f)
            if skill is not None:
                skills[skill.name] = skill
    return skills


def find_skill(name: str, *, start: Path | None = None) -> Skill | None:
    return discover_skills(start).get(name)
