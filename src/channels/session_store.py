"""
Channel session store — in-memory + JSON file persistence under data/channel_sessions/.
"""

from __future__ import annotations
import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone

_DATA_DIR = Path("data/channel_sessions")
_INDEX_FILE = _DATA_DIR / "index.json"


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> dict:
    _ensure_dir()
    if _INDEX_FILE.exists():
        with open(_INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_index(index: dict) -> None:
    _ensure_dir()
    with open(_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _session_path(session_id: str) -> Path:
    return _DATA_DIR / f"{session_id}.json"


def get_session(session_id: str) -> dict | None:
    """Load a session by ID. Returns None if not found."""
    _ensure_dir()
    path = _session_path(session_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_session(session_id: str, data: dict) -> dict:
    """Persist a session by ID."""
    _ensure_dir()
    data["session_id"] = session_id
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(_session_path(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Update index: channel+user_id → session_id
    index = _load_index()
    channel = data.get("channel", "unknown")
    user_id = data.get("external_user_id", "unknown")
    index[f"{channel}:{user_id}"] = session_id
    _save_index(index)
    return data


def find_session_by_user(channel: str, external_user_id: str) -> dict | None:
    """Find an active session by channel and external user ID."""
    index = _load_index()
    key = f"{channel}:{external_user_id}"
    session_id = index.get(key)
    if session_id is None:
        return None
    return get_session(session_id)


def create_session(channel: str, external_user_id: str, extra: dict | None = None) -> dict:
    """Create a new session for a channel user."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    data = {
        "session_id": session_id,
        "channel": channel,
        "external_user_id": external_user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }
    return save_session(session_id, data)
