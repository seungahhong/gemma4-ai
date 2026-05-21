from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest


class _FakeTokenizer:
    """apply_chat_template 호출을 가로채 메시지를 기록하는 더미 토크나이저."""

    def __init__(self, stub: MLXStub) -> None:
        self._stub = stub

    def apply_chat_template(self, chat, *, add_generation_prompt: bool = True, **_: object):
        self._stub.calls.append([dict(m) for m in chat])
        return [0]  # 프롬프트 토큰 ids 자리표시자 — 더미 stream에서는 쓰이지 않음


@dataclass
class MLXStub:
    """실제 MLX 추론 대신 고정 응답을 돌려주는 테스트 스텁.

    `response`로 모델 출력을 지정하고, CLI 실행 후 `last_user_content()` 등으로
    모델에 전달된 메시지를 검증한다(기존 respx 요청 본문 검사 대체).
    """

    response: str = ""
    calls: list = field(default_factory=list)  # apply_chat_template에 넘어온 chat 목록
    models: list = field(default_factory=list)  # 로드 요청된 model_id 목록

    @property
    def called(self) -> bool:
        return bool(self.calls)

    @property
    def last_messages(self) -> list:
        return self.calls[-1] if self.calls else []

    def last_user_content(self) -> str:
        return next(m["content"] for m in self.last_messages if m["role"] == "user")

    def last_system_content(self) -> str:
        return next(m["content"] for m in self.last_messages if m["role"] == "system")


@pytest.fixture
def mlx_stub(monkeypatch: pytest.MonkeyPatch) -> MLXStub:
    """mlx_client의 모델 로드/토큰 생성 시드를 더미로 대체한다(네트워크·모델 불필요)."""
    from gemma_cli.services import mlx_client

    stub = MLXStub()
    tokenizer = _FakeTokenizer(stub)

    def _fake_load(model_id: str):
        stub.models.append(model_id)
        return ("FAKE_MODEL", tokenizer)

    def _fake_stream(model, tokenizer, prompt, *, max_tokens, temperature):
        if stub.response:
            yield stub.response

    monkeypatch.setattr(mlx_client, "_load_model", _fake_load)
    monkeypatch.setattr(mlx_client, "_stream_tokens", _fake_stream)
    return stub


@pytest.fixture
def tmp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    yield home


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True, env=env)
    return repo
