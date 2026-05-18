from __future__ import annotations

import click

from gemma_cli.commands._common import load_cfg, make_client, run_async, stream_chat
from gemma_cli.services import prompts, session
from gemma_cli.services.ollama_client import Message


def _build_messages(history: list[Message], user_text: str) -> list[Message]:
    msgs: list[Message] = [Message("system", prompts.ASK_SYSTEM)]
    msgs.extend(history)
    msgs.append(Message("user", user_text))
    return msgs


@click.command(help="자유 질의. 단발성, -i 대화형, --resume으로 세션 재개.")
@click.argument("query", required=False)
@click.option("-i", "--interactive", is_flag=True, help="대화형 REPL 모드")
@click.option("--resume", "resume_id", default=None, help="세션 ID 또는 LAST")
@click.option("--new", is_flag=True, help="새 세션 시작")
def ask(query: str | None, interactive: bool, resume_id: str | None, new: bool) -> None:
    cfg = load_cfg()
    client = make_client(cfg, "ask")

    history: list[Message] = []
    sid: str | None = None
    if resume_id and not new:
        sid = session.resolve_session(resume_id)
        if not sid:
            click.secho(f"세션을 찾을 수 없습니다: {resume_id}", fg="yellow")
            return
        history = session.load(sid)
        click.secho(f"세션 재개: {sid} (메시지 {len(history)}개)", fg="cyan")

    if not interactive:
        if not query:
            raise click.UsageError("질문을 인자로 주거나 -i 모드를 사용하세요.")
        if sid is None:
            sid = session.new_session_id()
        messages = _build_messages(history, query)
        text = run_async(stream_chat(client, messages))
        assert isinstance(text, str)
        session.append(sid, Message("user", query))
        session.append(sid, Message("assistant", text))
        click.echo()
        click.secho(f"(세션 ID: {sid})", fg="bright_black")
        return

    if sid is None:
        sid = session.new_session_id()
    click.secho(f"대화형 모드 시작. :exit 으로 종료. (세션 {sid})", fg="cyan")
    while True:
        try:
            line = click.prompt("> ", prompt_suffix="").strip()
        except (EOFError, click.Abort):
            click.echo()
            break
        if line in (":exit", ":quit", ":q"):
            break
        if line == ":clear":
            history = []
            click.secho("히스토리 초기화", fg="cyan")
            continue
        if not line:
            continue
        messages = _build_messages(history, line)
        text = run_async(stream_chat(client, messages))
        assert isinstance(text, str)
        history.append(Message("user", line))
        history.append(Message("assistant", text))
        session.append(sid, Message("user", line))
        session.append(sid, Message("assistant", text))
        click.echo()
