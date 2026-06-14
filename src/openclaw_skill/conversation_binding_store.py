"""
Local file-based store for OpenClaw conversation-to-project bindings.
Supports both buyer/customer threads (b_side) and supplier/factory threads (m_side).
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

_DATA_DIR = Path("data/conversation_bindings")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConversationBinding(BaseModel):
    id: str = Field(default_factory=lambda: f"cb_{uuid.uuid4().hex[:12]}")
    source: str
    channel: str
    channel_account_id: str
    conversation_id: str
    sender_id: str
    sender_display_name: Optional[str] = None
    project_id: str
    b_workspace_id: Optional[str] = None
    procurement_edge_id: Optional[str] = None
    actor_id: Optional[str] = None
    role_context: str = "auto"
    mode: str = "auto"
    counterparty_type: str = "unknown"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _binding_path(binding_id: str) -> Path:
    return _DATA_DIR / f"{binding_id}.json"


def _load_all() -> list[ConversationBinding]:
    _ensure_dir()
    bindings = []
    for path in _DATA_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                bindings.append(ConversationBinding.model_validate(json.load(f)))
        except Exception:
            pass
    return bindings


def find_binding(
    source: str,
    channel: str,
    channel_account_id: str,
    conversation_id: str,
    sender_id: str,
) -> Optional[ConversationBinding]:
    for b in _load_all():
        if (
            b.source == source
            and b.channel == channel
            and b.channel_account_id == channel_account_id
            and b.conversation_id == conversation_id
            and b.sender_id == sender_id
        ):
            return b
    return None


def find_binding_by_project(project_id: str) -> list[ConversationBinding]:
    return [b for b in _load_all() if b.project_id == project_id]


def create_binding(
    source: str,
    channel: str,
    channel_account_id: str,
    conversation_id: str,
    sender_id: str,
    project_id: str,
    b_workspace_id: Optional[str] = None,
    procurement_edge_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    role_context: str = "auto",
    mode: str = "auto",
    counterparty_type: str = "unknown",
    sender_display_name: Optional[str] = None,
) -> ConversationBinding:
    _ensure_dir()
    binding = ConversationBinding(
        source=source,
        channel=channel,
        channel_account_id=channel_account_id,
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_display_name=sender_display_name,
        project_id=project_id,
        b_workspace_id=b_workspace_id,
        procurement_edge_id=procurement_edge_id,
        actor_id=actor_id,
        role_context=role_context,
        mode=mode,
        counterparty_type=counterparty_type,
    )
    _save(binding)
    return binding


def update_binding(binding: ConversationBinding) -> ConversationBinding:
    binding.updated_at = _utcnow()
    _save(binding)
    return binding


def _save(binding: ConversationBinding) -> None:
    _ensure_dir()
    path = _binding_path(binding.id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(binding.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
