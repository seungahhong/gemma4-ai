from __future__ import annotations

from gemma_cli.__main__ import rewrite_slash


def test_slash_command_rewritten() -> None:
    assert rewrite_slash(["gemma", "/commit"]) == ["gemma", "run", "commit"]


def test_slash_with_extra_args() -> None:
    assert rewrite_slash(["gemma", "/pr", "--base", "develop"]) == [
        "gemma", "run", "pr", "--base", "develop"
    ]


def test_no_slash_unchanged() -> None:
    assert rewrite_slash(["gemma", "commit"]) == ["gemma", "commit"]
    assert rewrite_slash(["gemma", "--help"]) == ["gemma", "--help"]
    assert rewrite_slash(["gemma"]) == ["gemma"]


def test_leading_options_skipped() -> None:
    # global options before the command should not block slash rewrite
    assert rewrite_slash(["gemma", "--version"]) == ["gemma", "--version"]


def test_double_slash_treated_as_path() -> None:
    # '//something' is unusual; do not rewrite (likely a path)
    assert rewrite_slash(["gemma", "//tmp/foo"]) == ["gemma", "//tmp/foo"]


def test_only_slash_not_rewritten() -> None:
    assert rewrite_slash(["gemma", "/"]) == ["gemma", "/"]
