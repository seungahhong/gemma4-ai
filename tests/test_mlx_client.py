from __future__ import annotations

import pytest

from gemma_cli.services import mlx_client
from gemma_cli.services.mlx_client import Message, MLXClient, MLXError


class _Tokenizer:
    """apply_chat_template로 넘어온 chat을 기록하는 더미 토크나이저."""

    def __init__(self) -> None:
        self.seen: list = []

    def apply_chat_template(self, chat, *, add_generation_prompt: bool = True, **_):
        self.seen.append([dict(m) for m in chat])
        return [1, 2, 3]


@pytest.fixture
def fake_model(monkeypatch: pytest.MonkeyPatch) -> _Tokenizer:
    tok = _Tokenizer()
    monkeypatch.setattr(mlx_client, "_load_model", lambda model_id: ("MODEL", tok))
    return tok


@pytest.mark.asyncio
async def test_chat_stream_concatenates_chunks(fake_model, monkeypatch) -> None:
    def fake_stream(model, tokenizer, prompt, *, max_tokens, temperature):
        yield from ["안녕", "하세요", " 반가워요"]

    monkeypatch.setattr(mlx_client, "_stream_tokens", fake_stream)
    client = MLXClient(model="test-model")
    out = "".join([c async for c in client.chat_stream([Message("user", "hi")])])
    assert out == "안녕하세요 반가워요"


@pytest.mark.asyncio
async def test_chat_stream_builds_prompt_from_messages(fake_model, monkeypatch) -> None:
    monkeypatch.setattr(
        mlx_client, "_stream_tokens", lambda *a, **k: iter(["ok"])
    )
    client = MLXClient(model="test-model")
    msgs = [Message("system", "지침"), Message("user", "질문")]
    _ = [c async for c in client.chat_stream(msgs)]
    # chat template에 system/user 메시지가 그대로 전달되어야 한다.
    assert fake_model.seen[-1] == [
        {"role": "system", "content": "지침"},
        {"role": "user", "content": "질문"},
    ]


@pytest.mark.asyncio
async def test_chat_stream_generation_error_wrapped(fake_model, monkeypatch) -> None:
    def boom(model, tokenizer, prompt, *, max_tokens, temperature):
        raise RuntimeError("kaboom")
        yield  # 제너레이터로 만들기 위한 도달 불가 구문

    monkeypatch.setattr(mlx_client, "_stream_tokens", boom)
    client = MLXClient(model="test-model")
    with pytest.raises(MLXError):
        async for _ in client.chat_stream([Message("user", "hi")]):
            pass


@pytest.mark.asyncio
async def test_chat_stream_load_error_propagates(monkeypatch) -> None:
    def bad_load(model_id):
        raise MLXError("모델 로드 실패")

    monkeypatch.setattr(mlx_client, "_load_model", bad_load)
    client = MLXClient(model="missing-model")
    with pytest.raises(MLXError) as exc:
        async for _ in client.chat_stream([Message("user", "hi")]):
            pass
    assert "모델 로드 실패" in str(exc.value)


def test_load_model_missing_package(monkeypatch) -> None:
    # mlx_lm import 실패 시 친절한 MLXError로 안내해야 한다.
    mlx_client._MODEL_CACHE.clear()
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "mlx_lm" or name.startswith("mlx_lm."):
            raise ImportError("no mlx_lm")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(MLXError) as exc:
        mlx_client._load_model("whatever")
    assert "mlx-lm" in str(exc.value)


def test_split_at_stop_truncates_at_marker() -> None:
    # 정지 마커 앞 텍스트만 남고 stop 신호가 켜진다(gemma의 <end_of_turn> 누출 방지).
    assert mlx_client._split_at_stop("안녕하세요<end_of_turn>") == ("안녕하세요", True)
    assert mlx_client._split_at_stop("그냥 텍스트") == ("그냥 텍스트", False)
    # 마커만 단독으로 온 조각은 빈 head + stop.
    assert mlx_client._split_at_stop("<eos>") == ("", True)
    # 여러 마커 중 가장 앞선 위치에서 잘린다.
    assert mlx_client._split_at_stop("a<eos>b<end_of_turn>") == ("a", True)


def test_load_model_caches(monkeypatch) -> None:
    mlx_client._MODEL_CACHE.clear()
    calls = {"n": 0}

    def fake_load(model_id):
        calls["n"] += 1
        return ("M", "T")

    # 캐시 동작만 확인 — 실제 mlx_lm.load 대신 캐시 채움
    mlx_client._MODEL_CACHE["cached-model"] = ("M", "T")
    assert mlx_client._load_model("cached-model") == ("M", "T")
    assert calls["n"] == 0  # 캐시 히트로 로더가 호출되지 않는다
