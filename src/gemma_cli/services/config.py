from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class CommandOverride(BaseModel):
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class Config(BaseModel):
    # MLX 모델 경로(HF 저장소 또는 로컬 디렉터리). 기본값은 텍스트 전용 e4b.
    # 주의: mlx-lm은 텍스트 전용 모델만 로드 가능 — gemma-4/gemma-3(4b+)의 멀티모달 변형은 로드 실패.
    model: str = "mlx-community/gemma-3n-E4B-it-lm-4bit"
    temperature: float = 0.2
    max_tokens: int = 2048
    commands: dict[str, CommandOverride] = Field(default_factory=dict)

    def for_command(self, name: str) -> tuple[str, float, int]:
        override = self.commands.get(name)
        model = override.model if override and override.model else self.model
        temp = override.temperature if override and override.temperature is not None else self.temperature
        max_tokens = (
            override.max_tokens if override and override.max_tokens is not None else self.max_tokens
        )
        return model, temp, max_tokens


def config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "gemma-cli" / "config.yaml"


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        return Config()
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Config.model_validate(raw)
