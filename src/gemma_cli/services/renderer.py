from __future__ import annotations

from collections.abc import AsyncIterator

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown


async def render_stream(stream: AsyncIterator[str], *, console: Console | None = None) -> str:
    console = console or Console()
    buffer: list[str] = []
    with Live(Markdown(""), console=console, refresh_per_second=12, transient=False) as live:
        async for chunk in stream:
            buffer.append(chunk)
            live.update(Markdown("".join(buffer)))
    return "".join(buffer)


async def collect_stream(stream: AsyncIterator[str]) -> str:
    parts: list[str] = []
    async for chunk in stream:
        parts.append(chunk)
    return "".join(parts)
