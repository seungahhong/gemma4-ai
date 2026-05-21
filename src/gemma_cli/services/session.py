from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from gemma_cli.services.mlx_client import Message


def sessions_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    d = base / "gemma-cli" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


def session_path(session_id: str, *, root: Path | None = None) -> Path:
    return (root or sessions_dir()) / f"{session_id}.jsonl"


def append(session_id: str, message: Message, *, root: Path | None = None) -> None:
    path = session_path(session_id, root=root)
    line = json.dumps({"role": message.role, "content": message.content}, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load(session_id: str, *, root: Path | None = None) -> list[Message]:
    path = session_path(session_id, root=root)
    if not path.exists():
        return []
    messages: list[Message] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        messages.append(Message(role=data["role"], content=data["content"]))
    return messages


def latest_session_id(*, root: Path | None = None) -> str | None:
    d = root or sessions_dir()
    files = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    return files[0].stem


def resolve_session(session_ref: str, *, root: Path | None = None) -> str | None:
    if session_ref.upper() == "LAST":
        return latest_session_id(root=root)
    return session_ref
