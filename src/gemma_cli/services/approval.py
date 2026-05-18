from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Literal

import click

Decision = Literal["yes", "no", "edit"]


def prompt_yne(question: str = "적용할까요?") -> Decision:
    while True:
        choice = click.prompt(f"{question} [y/N/e=편집]", default="N", show_default=False).strip().lower()
        if choice in ("y", "yes"):
            return "yes"
        if choice in ("", "n", "no"):
            return "no"
        if choice in ("e", "edit"):
            return "edit"
        click.echo("y / N / e 중 하나를 입력해주세요.")


def edit_in_editor(text: str, *, suffix: str = ".txt") -> str:
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile("w+", suffix=suffix, delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        subprocess.run([editor, path], check=False)
        with open(path, encoding="utf-8") as f:
            return f.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
