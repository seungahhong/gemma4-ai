from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from gemma_cli.services.renderer import collect_stream


async def _gen(parts: list[str]) -> AsyncIterator[str]:
    for p in parts:
        yield p


@pytest.mark.asyncio
async def test_collect_stream_concatenates() -> None:
    out = await collect_stream(_gen(["one", " ", "two"]))
    assert out == "one two"


@pytest.mark.asyncio
async def test_collect_stream_empty() -> None:
    out = await collect_stream(_gen([]))
    assert out == ""
