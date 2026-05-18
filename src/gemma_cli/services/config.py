from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class CommandOverride(BaseModel):
    model: str | None = None
    temperature: float | None = None


class Config(BaseModel):
    model: str = "gemma4:e4b"
    host: str = "http://localhost:11434"
    temperature: float = 0.2
    commands: dict[str, CommandOverride] = Field(default_factory=dict)

    def for_command(self, name: str) -> tuple[str, float]:
        override = self.commands.get(name)
        model = override.model if override and override.model else self.model
        temp = override.temperature if override and override.temperature is not None else self.temperature
        return model, temp


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
