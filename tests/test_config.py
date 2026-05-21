from __future__ import annotations

from pathlib import Path

import yaml

from gemma_cli.services.config import Config, load_config


def test_default_config_when_missing(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nope.yaml")
    assert cfg.model == "mlx-community/gemma-3n-E4B-it-lm-4bit"
    assert cfg.temperature == 0.2
    assert cfg.max_tokens == 2048


def test_legacy_host_field_is_ignored(tmp_path: Path) -> None:
    # 기존 ollama용 config.yaml(host 포함)도 오류 없이 로드되어야 한다.
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"model": "mlx-community/foo", "host": "http://localhost:11434"}))
    cfg = load_config(path)
    assert cfg.model == "mlx-community/foo"
    assert not hasattr(cfg, "host")


def test_loads_yaml_overrides(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "model": "mlx-community/gemma-3-text-27b-it-4bit",
                "temperature": 0.8,
                "commands": {"refactor": {"model": "mlx-community/gemma-3n-E4B-it-lm-4bit"}},
            }
        )
    )
    cfg = load_config(path)
    assert cfg.model == "mlx-community/gemma-3-text-27b-it-4bit"
    assert cfg.for_command("refactor") == ("mlx-community/gemma-3n-E4B-it-lm-4bit", 0.8, 2048)
    assert cfg.for_command("review") == ("mlx-community/gemma-3-text-27b-it-4bit", 0.8, 2048)


def test_per_command_temperature_override() -> None:
    cfg = Config.model_validate(
        {"commands": {"ask": {"temperature": 0.9}}}
    )
    default = "mlx-community/gemma-3n-E4B-it-lm-4bit"
    assert cfg.for_command("ask") == (default, 0.9, 2048)
    assert cfg.for_command("commit") == (default, 0.2, 2048)


def test_per_command_max_tokens_override() -> None:
    cfg = Config.model_validate(
        {"max_tokens": 1024, "commands": {"analyze": {"max_tokens": 4096}}}
    )
    default = "mlx-community/gemma-3n-E4B-it-lm-4bit"
    assert cfg.for_command("analyze") == (default, 0.2, 4096)
    assert cfg.for_command("ask") == (default, 0.2, 1024)
