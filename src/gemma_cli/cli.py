from __future__ import annotations

import click

from gemma_cli import __version__
from gemma_cli.commands import analyze as analyze_cmd
from gemma_cli.commands import ask as ask_cmd
from gemma_cli.commands import commit as commit_cmd
from gemma_cli.commands import pr as pr_cmd
from gemma_cli.commands import refactor as refactor_cmd
from gemma_cli.commands import review as review_cmd
from gemma_cli.commands import skills as skills_cmd
from gemma_cli.services import skills as skills_svc


class SkillGroup(click.Group):
    """빌트인 커맨드에 더해, 발견된 사용자 정의 스킬을 1급 커맨드로 노출한다.

    `.gemma/skills/<name>.md`(프로젝트) 또는 전역 스킬을 추가하기만 하면
    코드 수정 없이 `gemma <name>`로 호출되고 `gemma --help`에도 나타난다.
    빌트인과 이름이 겹치면(`commit`, `pr`) 빌트인이 우선이며, 스킬은
    슬래시 별칭(`gemma /commit` → `run commit`)으로 호출한다.
    """

    def _discover(self) -> dict[str, skills_svc.Skill]:
        try:
            return skills_svc.discover_skills()
        except Exception:
            # 스킬 디스커버리 실패가 빌트인 사용을 막아선 안 된다.
            return {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        builtins = set(super().list_commands(ctx))
        return sorted(builtins | set(self._discover().keys()))

    def get_command(self, ctx: click.Context, name: str) -> click.Command | None:
        builtin = super().get_command(ctx, name)
        if builtin is not None:
            return builtin
        skill = self._discover().get(name)
        if skill is None:
            return None
        return skills_cmd.make_skill_command(skill)


@click.group(cls=SkillGroup, help="gemma4 + MLX 기반 로컬 개발 보조 CLI")
@click.version_option(__version__, prog_name="gemma")
def cli() -> None:
    pass


cli.add_command(review_cmd.review)
cli.add_command(commit_cmd.commit)
cli.add_command(pr_cmd.pr)
cli.add_command(refactor_cmd.refactor)
cli.add_command(analyze_cmd.analyze)
cli.add_command(ask_cmd.ask)
cli.add_command(skills_cmd.skills_list)
cli.add_command(skills_cmd.skills_run)
