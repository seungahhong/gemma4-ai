from __future__ import annotations

import click

from gemma_cli.commands._common import load_cfg, make_client, run_async, stream_chat
from gemma_cli.services import approval, git_ops, prompts
from gemma_cli.services.ollama_client import Message


@click.command(help="스테이징된 변경사항으로 커밋 메시지를 생성하고 승인을 받는다.")
def commit() -> None:
    if not git_ops.is_repo():
        raise click.UsageError("git 저장소가 아닙니다.")
    diff = git_ops.staged_diff()
    if not diff.strip():
        click.echo("스테이징된 변경이 없습니다. `git add` 후 다시 시도해주세요.")
        return

    cfg = load_cfg()
    client = make_client(cfg, "commit")
    messages = [
        Message("system", prompts.COMMIT),
        Message("user", f"```diff\n{diff}\n```"),
    ]
    text = run_async(stream_chat(client, messages, render=False))
    assert isinstance(text, str)
    message = text.strip()
    if not message:
        click.echo("생성된 메시지가 비어 있습니다.")
        return

    click.echo()
    click.secho("=== 생성된 커밋 메시지 ===", fg="cyan")
    click.echo(message)
    click.echo()

    decision = approval.prompt_yne("이 메시지로 커밋할까요?")
    if decision == "edit":
        message = approval.edit_in_editor(message, suffix=".gitcommit").strip()
        if not message:
            click.echo("메시지가 비어 있어 취소합니다.")
            return
        click.secho("=== 편집된 메시지 ===", fg="cyan")
        click.echo(message)
        decision = approval.prompt_yne("이대로 커밋할까요?")

    if decision != "yes":
        click.echo("취소되었습니다.")
        return

    try:
        git_ops.commit(message)
        click.secho("✓ 커밋 완료", fg="green")
    except git_ops.GitError as e:
        click.secho(f"커밋 실패: {e}", fg="red", err=True)
        raise click.exceptions.Exit(1) from e
