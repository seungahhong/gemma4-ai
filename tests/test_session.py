from __future__ import annotations

import json
from pathlib import Path

from gemma_cli.services import session
from gemma_cli.services.mlx_client import Message


def test_append_and_load_roundtrip(tmp_path: Path) -> None:
    sid = session.new_session_id()
    session.append(sid, Message("user", "안녕"), root=tmp_path)
    session.append(sid, Message("assistant", "반갑습니다"), root=tmp_path)
    msgs = session.load(sid, root=tmp_path)
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[0].content == "안녕"
    assert msgs[1].content == "반갑습니다"


def test_jsonl_format_preserves_korean(tmp_path: Path) -> None:
    sid = session.new_session_id()
    session.append(sid, Message("user", "한글 메시지"), root=tmp_path)
    path = session.session_path(sid, root=tmp_path)
    line = path.read_text(encoding="utf-8").splitlines()[0]
    parsed = json.loads(line)
    assert parsed["content"] == "한글 메시지"


def test_multiple_sessions_isolated(tmp_path: Path) -> None:
    a = session.new_session_id()
    b = session.new_session_id()
    assert a != b
    session.append(a, Message("user", "A"), root=tmp_path)
    session.append(b, Message("user", "B"), root=tmp_path)
    assert session.load(a, root=tmp_path)[0].content == "A"
    assert session.load(b, root=tmp_path)[0].content == "B"


def test_resolve_session_last(tmp_path: Path, monkeypatch) -> None:
    import time

    first = session.new_session_id()
    session.append(first, Message("user", "1"), root=tmp_path)
    time.sleep(0.02)
    second = session.new_session_id()
    session.append(second, Message("user", "2"), root=tmp_path)

    assert session.latest_session_id(root=tmp_path) == second
    assert session.resolve_session("LAST", root=tmp_path) == second
    assert session.resolve_session(first, root=tmp_path) == first


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    assert session.load("nonexistent", root=tmp_path) == []
