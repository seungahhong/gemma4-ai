from __future__ import annotations

from pathlib import Path

import yaml

from gemma_cli.services.config import Config, load_config


def test_default_config_when_missing(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nope.yaml")
    assert cfg.model == "gemma4:e4b"
    assert cfg.host.startswith("http://localhost:11434")
    assert cfg.temperature == 0.2


def test_loads_yaml_overrides(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "model": "gemma4:26b",
                "temperature": 0.8,
                "commands": {"refactor": {"model": "gemma4:e2b"}},
            }
        )
    )
    cfg = load_config(path)
    assert cfg.model == "gemma4:26b"
    assert cfg.for_command("refactor") == ("gemma4:e2b", 0.8)
    assert cfg.for_command("review") == ("gemma4:26b", 0.8)


def test_per_command_temperature_override() -> None:
    cfg = Config.model_validate(
        {"commands": {"ask": {"temperature": 0.9}}}
    )
    assert cfg.for_command("ask") == ("gemma4:e4b", 0.9)
    assert cfg.for_command("commit") == ("gemma4:e4b", 0.2)
