from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx


@dataclass
class Message:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, host: str, model: str, temperature: float = 0.2):
        self.host = host.rstrip("/")
        self.model = model
        self.temperature = temperature

    async def chat_stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            "options": {"temperature": temperature if temperature is not None else self.temperature},
        }
        url = f"{self.host}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=None, write=10.0, pool=5.0)) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        raise OllamaError(
                            f"ollama 호출 실패 ({resp.status_code}): {body.decode(errors='replace')[:200]}"
                        )
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if chunk.get("done"):
                            break
                        msg = chunk.get("message") or {}
                        content = msg.get("content", "")
                        if content:
                            yield content
        except httpx.ConnectError as e:
            raise OllamaError(
                "ollama 서버에 연결할 수 없습니다. `ollama serve`가 실행 중인지 확인해주세요."
            ) from e
