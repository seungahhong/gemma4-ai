from __future__ import annotations

from pathlib import Path

import click

from gemma_cli.commands._common import load_cfg, make_client, read_path_content, run_async, stream_chat
from gemma_cli.services import prompts
from gemma_cli.services.mlx_client import Message


@click.command(help="코드/디렉터리 구조와 의존성을 분석한다.")
@click.argument("target", required=False, type=click.Path(exists=True, path_type=Path))
def analyze(target: Path | None) -> None:
    path = target or Path.cwd()
    body = read_path_content(path)
    if not body.strip():
        click.echo("분석할 파일을 찾지 못했습니다.")
        return
    cfg = load_cfg()
    client = make_client(cfg, "analyze")
    messages = [
        Message("system", prompts.ANALYZE),
        Message("user", f"분석 대상: {path}\n\n{body[:80_000]}"),
    ]
    run_async(stream_chat(client, messages))
