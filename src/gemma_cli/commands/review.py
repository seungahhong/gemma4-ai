from __future__ import annotations

from pathlib import Path

import click

from gemma_cli.commands._common import load_cfg, make_client, read_path_content, run_async, stream_chat
from gemma_cli.services import git_ops, prompts
from gemma_cli.services.mlx_client import Message


@click.command(help="코드 리뷰. 인자가 없으면 git diff(staged 우선)를 사용한다.")
@click.argument("target", required=False, type=click.Path(exists=True, path_type=Path))
def review(target: Path | None) -> None:
    if target is None:
        if not git_ops.is_repo():
            raise click.UsageError("git 저장소가 아닙니다. 파일 경로를 지정하거나 git 저장소에서 실행하세요.")
        diff = git_ops.staged_diff() or git_ops.unstaged_diff()
        if not diff.strip():
            click.echo("변경사항이 없습니다.")
            return
        user_content = f"다음 diff를 리뷰해주세요.\n\n```diff\n{diff}\n```"
    else:
        body = read_path_content(target)
        user_content = f"다음 코드를 리뷰해주세요. 경로: {target}\n\n{body}"

    cfg = load_cfg()
    client = make_client(cfg, "review")
    messages = [Message("system", prompts.REVIEW), Message("user", user_content)]
    run_async(stream_chat(client, messages))
