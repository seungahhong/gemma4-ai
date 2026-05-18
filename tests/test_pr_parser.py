from __future__ import annotations

from gemma_cli.commands.pr import _split_title_body


def test_split_title_body_basic() -> None:
    text = """TITLE: feat(api): 사용자 인증 추가
---
## 요약
- A
- B

## 테스트 계획
- [ ] login
"""
    title, body = _split_title_body(text)
    assert title == "feat(api): 사용자 인증 추가"
    assert body.startswith("## 요약")
    assert "- [ ] login" in body


def test_split_no_title_returns_empty() -> None:
    text = "그냥 텍스트\n---\n본문"
    title, body = _split_title_body(text)
    assert title == ""


def test_split_title_only_no_body() -> None:
    text = "TITLE: 단독 제목\n---\n"
    title, body = _split_title_body(text)
    assert title == "단독 제목"
    assert body == ""
