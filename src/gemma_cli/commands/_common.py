from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from pathlib import Path

import click

from gemma_cli.services.config import Config, load_config
from gemma_cli.services.instructions import with_instructions
from gemma_cli.services.mlx_client import Message, MLXClient, MLXError
from gemma_cli.services.renderer import collect_stream, render_stream


def run_async(coro: Awaitable[object]) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


def make_client(cfg: Config, command_name: str) -> MLXClient:
    model, temp, max_tokens = cfg.for_command(command_name)
    return MLXClient(model=model, temperature=temp, max_tokens=max_tokens)


def load_cfg() -> Config:
    return load_config()


def read_path_content(path: Path) -> str:
    if path.is_dir():
        chunks: list[str] = []
        for p in sorted(path.rglob("*")):
            if p.is_file() and not _ignored(p) and p.stat().st_size < 50_000:
                rel = p.relative_to(path)
                chunks.append(f"### {rel}\n```\n{p.read_text(errors='replace')}\n```")
        return "\n\n".join(chunks)
    return path.read_text(errors="replace")


def _ignored(p: Path) -> bool:
    parts = set(p.parts)
    bad = {".git", "__pycache__", ".venv", "node_modules", "dist", "build", ".pytest_cache"}
    return bool(parts & bad)


def apply_instructions(messages: list[Message]) -> list[Message]:
    if not messages or messages[0].role != "system":
        return messages
    new_first = Message("system", with_instructions(messages[0].content))
    return [new_first, *messages[1:]]


async def stream_chat(client: MLXClient, messages: list[Message], *, render: bool = True) -> str:
    messages = apply_instructions(messages)
    try:
        if render:
            return await render_stream(client.chat_stream(messages))
        return await collect_stream(client.chat_stream(messages))
    except MLXError as e:
        click.secho(f"오류: {e}", fg="red", err=True)
        raise click.exceptions.Exit(1) from e
