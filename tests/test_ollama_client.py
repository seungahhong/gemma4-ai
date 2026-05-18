from __future__ import annotations

import json

import httpx
import pytest
import respx

from gemma_cli.services.ollama_client import Message, OllamaClient, OllamaError


def _make_stream_bytes(chunks: list[str]) -> bytes:
    lines = [json.dumps({"message": {"role": "assistant", "content": c}, "done": False}) for c in chunks]
    lines.append(json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}))
    return ("\n".join(lines) + "\n").encode()


@pytest.mark.asyncio
async def test_chat_stream_concatenates_chunks() -> None:
    body = _make_stream_bytes(["안녕", "하세요", " 반가워요"])
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=httpx.Response(200, content=body))
        client = OllamaClient(host="http://localhost:11434", model="gemma4:e4b")
        out = "".join([c async for c in client.chat_stream([Message("user", "hi")])])
    assert out == "안녕하세요 반가워요"


@pytest.mark.asyncio
async def test_chat_stream_non_200_raises() -> None:
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(return_value=httpx.Response(500, content=b"boom"))
        client = OllamaClient(host="http://localhost:11434", model="gemma4:e4b")
        with pytest.raises(OllamaError):
            async for _ in client.chat_stream([Message("user", "hi")]):
                pass


@pytest.mark.asyncio
async def test_chat_stream_connect_error() -> None:
    with respx.mock(base_url="http://localhost:11434") as mock:
        mock.post("/api/chat").mock(side_effect=httpx.ConnectError("no"))
        client = OllamaClient(host="http://localhost:11434", model="gemma4:e4b")
        with pytest.raises(OllamaError) as exc:
            async for _ in client.chat_stream([Message("user", "hi")]):
                pass
        assert "ollama" in str(exc.value)
