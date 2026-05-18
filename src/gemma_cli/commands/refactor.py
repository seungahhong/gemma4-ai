from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.syntax import Syntax

from gemma_cli.commands._common import load_cfg, make_client, run_async, stream_chat
from gemma_cli.services import approval, git_ops, prompts
from gemma_cli.services.ollama_client import Message


def _clean_diff(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip() + "\n"


@click.command(help="파일 리팩토링을 unified diff로 받아서 미리보기 후 적용한다.")
@click.argument("target", type=click.Path(exists=True, path_type=Path))
@click.option("-i", "--instruction", default="가독성과 유지보수성을 개선해줘.", help="리팩토링 지시사항")
def refactor(target: Path, instruction: str) -> None:
    if target.is_dir():
        raise click.UsageError("refactor는 단일 파일만 지원합니다.")
    body = target.read_text(errors="replace")
    user = (
        f"리팩토링 지시: {instruction}\n\n"
        f"파일 경로: {target}\n\n"
        f"현재 내용:\n```\n{body}\n```\n\n"
        f"위 경로 기준 unified diff를 출력하세요. (--- a/{target} 와 +++ b/{target})"
    )
    cfg = load_cfg()
    client = make_client(cfg, "refactor")
    messages = [Message("system", prompts.REFACTOR), Message("user", user)]
    text = run_async(stream_chat(client, messages, render=False))
    assert isinstance(text, str)
    diff = _clean_diff(text)
    if not diff.strip() or "@@" not in diff:
        click.echo("제안된 변경사항이 없습니다.")
        return

    console = Console()
    console.print("[cyan]=== 제안된 변경사항 (diff) ===[/cyan]")
    console.print(Syntax(diff, "diff", theme="ansi_dark", word_wrap=True))

    decision = approval.prompt_yne("이 변경을 적용할까요?")
    if decision == "edit":
        diff = approval.edit_in_editor(diff, suffix=".patch")
        decision = approval.prompt_yne("편집된 diff를 적용할까요?")

    if decision != "yes":
        click.echo("취소되었습니다.")
        return

    try:
        git_ops.apply_patch(diff)
        click.secho("✓ 적용 완료", fg="green")
    except git_ops.GitError as e:
        click.secho(f"패치 적용 실패: {e}", fg="red", err=True)
        click.secho("원본은 변경되지 않았습니다. 필요 시 수동으로 적용하세요.", fg="yellow")
        raise click.exceptions.Exit(1) from e
