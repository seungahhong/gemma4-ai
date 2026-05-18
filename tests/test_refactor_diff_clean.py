from __future__ import annotations

from gemma_cli.commands.refactor import _clean_diff


def test_strips_diff_fence() -> None:
    raw = "```diff\n--- a/x\n+++ b/x\n@@\n-old\n+new\n```\n"
    out = _clean_diff(raw)
    assert out.startswith("--- a/x")
    assert "```" not in out


def test_passes_through_plain_diff() -> None:
    raw = "--- a/x\n+++ b/x\n@@\n-old\n+new\n"
    out = _clean_diff(raw)
    assert "--- a/x" in out
    assert "+new" in out


def test_trailing_newline_added() -> None:
    raw = "--- a/x\n+++ b/x\n@@\n+x"
    out = _clean_diff(raw)
    assert out.endswith("\n")
