from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from gemma_cli.commands._common import load_cfg, make_client, run_async, stream_chat
from gemma_cli.services import actions as actions_svc
from gemma_cli.services import skills as skills_svc
from gemma_cli.services.mlx_client import Message


@click.command("skills", help="사용 가능한 사용자 정의 스킬 목록을 보여준다.")
def skills_list() -> None:
    found = skills_svc.discover_skills()
    if not found:
        click.echo("등록된 스킬이 없습니다.")
        click.echo("  사용자 스킬: ~/.config/gemma-cli/skills/<이름>.md")
        click.echo("  프로젝트 스킬: ./.gemma/skills/<이름>.md")
        return
    table = Table(title="등록된 스킬")
    table.add_column("이름", style="cyan")
    table.add_column("설명")
    table.add_column("input", style="magenta")
    table.add_column("action", style="yellow")
    table.add_column("출처", style="bright_black")
    for skill in found.values():
        table.add_row(
            skill.name,
            skill.description,
            skill.input_source,
            skill.action,
            str(skill.source),
        )
    Console().print(table)


def _parse_arg(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise click.BadParameter(f"--arg는 KEY=VAL 형식이어야 합니다: {value}")
    k, v = value.split("=", 1)
    return k.strip(), v


def run_skill(
    skill: skills_svc.Skill,
    *,
    input_path: Path | None = None,
    args_raw: tuple[str, ...] = (),
    input_text: str | None = None,
    base: str | None = None,
) -> None:
    """스킬 1개를 입력 수집 → 렌더 → MLX 호출 → action 순서로 실행한다.

    `run` 빌트인 커맨드와 동적으로 등록된 스킬 커맨드가 공유하는 핵심 로직.
    """
    content = ""
    if input_text is not None:
        content = input_text
    elif input_path is not None:
        if input_path.is_dir():
            content = "\n\n".join(
                f"### {p.relative_to(input_path)}\n```\n{p.read_text(errors='replace')}\n```"
                for p in sorted(input_path.rglob("*"))
                if p.is_file() and p.stat().st_size < 50_000
            )
        else:
            content = input_path.read_text(errors="replace")
    elif skill.input_source != "manual":
        content = actions_svc.collect_input(skill.input_source, base=base or skill.base)

    template_args = dict(_parse_arg(v) for v in args_raw)
    rendered = skill.render(input_text=content, args=template_args)

    cfg = load_cfg()
    client = make_client(cfg, "run")
    messages = [
        Message("system", "당신은 한국어로 답하는 개발 도우미입니다. 아래 사용자 정의 스킬 지시를 따르세요."),
        Message("user", rendered),
    ]
    render_live = skill.action == "print"
    response = run_async(stream_chat(client, messages, render=render_live))
    assert isinstance(response, str)

    if skill.action != "print":
        rc = actions_svc.execute_action(skill.action, response)
        if rc != 0:
            raise click.exceptions.Exit(rc)


def make_skill_command(skill: skills_svc.Skill) -> click.Command:
    """발견된 스킬을 1급 Click 커맨드로 변환한다.

    `gemma <스킬명> [INPUT_PATH] [--arg K=V] [--input TEXT] [--base B]` 형태로
    `gemma run <스킬명>`과 동일하게 동작한다. `SkillGroup`이 동적으로 호출한다.
    """
    desc = skill.description or "(설명 없음)"

    @click.command(
        name=skill.name,
        short_help=f"[스킬] {desc}",
        help=f"[사용자 정의 스킬] {desc}\n\n출처: {skill.source}",
    )
    @click.argument("input_path", required=False, type=click.Path(exists=True, path_type=Path))
    @click.option("--arg", "args_raw", multiple=True, help="템플릿 변수 KEY=VAL (다중 지정 가능)")
    @click.option("--input", "input_text", default=None, help="입력 텍스트를 인라인으로 전달")
    @click.option("--base", default=None, help="branch-diff input 사용 시 base 브랜치 오버라이드")
    def _skill_cmd(
        input_path: Path | None,
        args_raw: tuple[str, ...],
        input_text: str | None,
        base: str | None,
    ) -> None:
        run_skill(
            skill,
            input_path=input_path,
            args_raw=args_raw,
            input_text=input_text,
            base=base,
        )

    return _skill_cmd


@click.command("run", help="등록된 스킬을 실행한다.")
@click.argument("name")
@click.argument("input_path", required=False, type=click.Path(exists=True, path_type=Path))
@click.option("--arg", "args_raw", multiple=True, help="템플릿 변수 KEY=VAL (다중 지정 가능)")
@click.option("--input", "input_text", default=None, help="입력 텍스트를 인라인으로 전달")
@click.option("--base", default=None, help="branch-diff input 사용 시 base 브랜치 오버라이드")
def skills_run(
    name: str,
    input_path: Path | None,
    args_raw: tuple[str, ...],
    input_text: str | None,
    base: str | None,
) -> None:
    skill = skills_svc.find_skill(name)
    if skill is None:
        available = ", ".join(skills_svc.discover_skills().keys()) or "(없음)"
        raise click.UsageError(f"스킬을 찾을 수 없습니다: {name}\n사용 가능: {available}")

    run_skill(
        skill,
        input_path=input_path,
        args_raw=args_raw,
        input_text=input_text,
        base=base,
    )
