from __future__ import annotations

import shutil
import subprocess

import click

from gemma_cli.commands._common import load_cfg, make_client, run_async, stream_chat
from gemma_cli.services import approval, git_ops, prompts
from gemma_cli.services.ollama_client import Message


def _split_title_body(text: str) -> tuple[str, str]:
    lines = text.strip().splitlines()
    title = ""
    body_lines: list[str] = []
    state = "title"
    for line in lines:
        if state == "title":
            if line.upper().startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()
                state = "wait_sep"
            elif line.strip() == "---":
                state = "body"
        elif state == "wait_sep":
            if line.strip() == "---":
                state = "body"
        else:
            body_lines.append(line)
    return title, "\n".join(body_lines).strip()


@click.command(help="현재 브랜치에서 base까지의 변경을 기반으로 PR 제목/본문을 생성한다.")
@click.option("--base", default="main", show_default=True, help="비교 기준 브랜치")
def pr(base: str) -> None:
    if not git_ops.is_repo():
        raise click.UsageError("git 저장소가 아닙니다.")
    try:
        diff = git_ops.branch_diff(base)
        log = git_ops.branch_log(base)
    except git_ops.GitError as e:
        raise click.UsageError(str(e)) from e
    if not diff.strip():
        click.echo(f"{base}와 비교한 변경사항이 없습니다.")
        return

    cfg = load_cfg()
    client = make_client(cfg, "pr")
    user = f"## 커밋 로그\n{log}\n\n## diff\n```diff\n{diff}\n```"
    messages = [Message("system", prompts.PR), Message("user", user)]
    text = run_async(stream_chat(client, messages, render=False))
    assert isinstance(text, str)
    title, body = _split_title_body(text)
    if not title:
        click.secho("PR 제목 추출 실패. 원본 출력:", fg="yellow")
        click.echo(text)
        return

    click.echo()
    click.secho("=== PR 제목 ===", fg="cyan")
    click.echo(title)
    click.secho("=== PR 본문 ===", fg="cyan")
    click.echo(body)
    click.echo()

    decision = approval.prompt_yne("이 내용으로 PR을 생성할까요?")
    if decision == "edit":
        edited = approval.edit_in_editor(f"{title}\n---\n{body}", suffix=".md")
        parts = edited.split("\n---\n", 1)
        if len(parts) == 2:
            title, body = parts[0].strip(), parts[1].strip()
        decision = approval.prompt_yne("이대로 PR을 생성할까요?")

    if decision != "yes":
        click.echo("취소되었습니다.")
        return

    if shutil.which("gh") is None:
        click.secho("`gh` CLI가 설치되어 있지 않습니다. 수동으로 PR을 생성해주세요.", fg="yellow")
        click.echo(f"제목: {title}")
        click.echo("본문:")
        click.echo(body)
        return

    res = subprocess.run(
        ["gh", "pr", "create", "--title", title, "--body", body],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        click.secho(f"gh pr create 실패: {res.stderr.strip()}", fg="red", err=True)
        raise click.exceptions.Exit(1)
    click.secho(res.stdout.strip(), fg="green")
