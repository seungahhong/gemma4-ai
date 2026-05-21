from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class MLXError(RuntimeError):
    pass


# 모델 로드는 비용이 크므로 (model, tokenizer)를 모델 id별로 캐시한다.
_MODEL_CACHE: dict[str, tuple[Any, Any]] = {}


def _load_model(model_id: str) -> tuple[Any, Any]:
    """MLX 모델과 토크나이저를 로드(필요 시 다운로드)하고 캐시한다."""
    cached = _MODEL_CACHE.get(model_id)
    if cached is not None:
        return cached
    try:
        from mlx_lm import load
    except ImportError as e:  # mlx-lm 미설치
        raise MLXError(
            "mlx-lm 패키지가 설치되어 있지 않습니다. `uv pip install mlx-lm`로 설치해주세요."
        ) from e
    try:
        pair = load(model_id)
    except Exception as e:  # 모델 경로 오류·다운로드 실패 등
        raise MLXError(
            f"MLX 모델을 로드할 수 없습니다 ({model_id}): {e}\n"
            "config.yaml의 model 값이 올바른 MLX 모델 경로인지 확인해주세요."
        ) from e
    _MODEL_CACHE[model_id] = pair
    return pair


def _build_prompt(tokenizer: Any, messages: list[Message]) -> Any:
    """채팅 메시지를 모델의 chat template으로 프롬프트(토큰 ids)로 변환한다."""
    chat = [m.to_dict() for m in messages]
    return tokenizer.apply_chat_template(chat, add_generation_prompt=True)


# 일부 모델(예: gemma)은 턴 종료 토큰을 EOS로 등록하지 않아 생성이 멈추지 않고
# 특수 토큰이 출력 텍스트에 그대로 새어나온다. 이를 정지 신호로 처리한다.
_STOP_MARKERS = ("<end_of_turn>", "<eos>", "<|im_end|>", "<|endoftext|>")


def _split_at_stop(text: str) -> tuple[str, bool]:
    """정지 마커가 있으면 그 앞부분만 돌려주고 stop=True를 반환한다."""
    earliest: int | None = None
    for marker in _STOP_MARKERS:
        i = text.find(marker)
        if i != -1 and (earliest is None or i < earliest):
            earliest = i
    if earliest is None:
        return text, False
    return text[:earliest], True


def _stream_tokens(
    model: Any,
    tokenizer: Any,
    prompt: Any,
    *,
    max_tokens: int,
    temperature: float,
) -> Iterator[str]:
    """mlx_lm.stream_generate 래퍼 — 생성된 텍스트 조각을 순차적으로 yield한다."""
    from mlx_lm import stream_generate
    from mlx_lm.sample_utils import make_sampler

    sampler = make_sampler(temp=temperature)
    for resp in stream_generate(
        model, tokenizer, prompt, max_tokens=max_tokens, sampler=sampler
    ):
        text = getattr(resp, "text", "")
        if not text:
            continue
        head, stop = _split_at_stop(text)
        if head:
            yield head
        if stop:
            return


class MLXClient:
    def __init__(self, model: str, temperature: float = 0.2, max_tokens: int = 2048):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def chat_stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        model_id = model or self.model
        temp = temperature if temperature is not None else self.temperature

        # MLX 스트림은 스레드-로컬이므로 모델 로드와 생성을 반드시 같은 스레드에서 수행한다.
        # (다른 스레드에서 로드하면 "There is no Stream(gpu, N) in current thread" 오류가 난다.)
        mdl, tokenizer = _load_model(model_id)
        prompt = _build_prompt(tokenizer, messages)

        try:
            for piece in _stream_tokens(
                mdl, tokenizer, prompt, max_tokens=self.max_tokens, temperature=temp
            ):
                if piece:
                    yield piece
                    await asyncio.sleep(0)  # 토큰마다 이벤트 루프에 양보(렌더 갱신)
        except MLXError:
            raise
        except Exception as e:  # 생성 중 예기치 못한 오류
            raise MLXError(f"MLX 생성 중 오류가 발생했습니다: {e}") from e
