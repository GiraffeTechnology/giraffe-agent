"""
ConversationThread — one per edge-level conversation, with routing metadata.
Persisted as JSON under data/communication/threads/.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/communication/threads")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationThread(BaseModel):
    thread_id: str
    project_id: str
    edge_id: str
    from_actor_id: str
    to_actor_id: str
    channel_type: Literal["wechat", "whatsapp", "openclaw", "line", "email", "web_fallback", "mock"]
    thread_type: Literal[
        "buyer_main_supplier",
        "main_supplier_upstream",
        "main_supplier_internal_approval",
        "buyer_rollup_review",
        "production_progress",
        "media_confirmation",
        "logistics_handover",
        "logistics_tracking_update",
        "exception_resolution",
        "buyer_signoff",
    ]
    active_role_context_id: str
    status: Literal["OPEN", "WAITING_FOR_REPLY", "REPLIED", "CLOSED", "ESCALATED"] = "OPEN"
    correlation_token: str | None = None
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


def create_thread(
    project_id: str,
    edge_id: str,
    from_actor_id: str,
    to_actor_id: str,
    thread_type: str,
    active_role_context_id: str,
    channel_type: str = "mock",
    correlation_token: str | None = None,
) -> ConversationThread:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    thread = ConversationThread(
        thread_id=f"THREAD-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        edge_id=edge_id,
        from_actor_id=from_actor_id,
        to_actor_id=to_actor_id,
        channel_type=channel_type,  # type: ignore[arg-type]
        thread_type=thread_type,  # type: ignore[arg-type]
        active_role_context_id=active_role_context_id,
        correlation_token=correlation_token,
    )
    _save_thread(thread)
    log_m_event(
        event_type="CONVERSATION_THREAD_CREATED",
        b_workspace_id=project_id,
        payload={"thread_id": thread.thread_id, "thread_type": thread_type},
    )
    return thread


def _save_thread(thread: ConversationThread) -> ConversationThread:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    thread.updated_at = _utcnow()
    path = _DATA_DIR / f"{thread.thread_id}.json"
    path.write_text(thread.model_dump_json(indent=2), encoding="utf-8")
    return thread


def get_thread(thread_id: str) -> ConversationThread:
    path = _DATA_DIR / f"{thread_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Thread not found: {thread_id}")
    return ConversationThread.model_validate(json.loads(path.read_text(encoding="utf-8")))


def update_thread_status(thread_id: str, status: str) -> ConversationThread:
    thread = get_thread(thread_id)
    thread.status = status  # type: ignore[assignment]
    return _save_thread(thread)


def get_threads_for_project(project_id: str) -> list[ConversationThread]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    threads = []
    for p in _DATA_DIR.glob("THREAD-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            t = ConversationThread.model_validate(data)
            if t.project_id == project_id:
                threads.append(t)
        except Exception:
            pass
    return threads
