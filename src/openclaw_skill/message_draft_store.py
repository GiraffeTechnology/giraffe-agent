"""
Local file-based store for message drafts with human approval workflow.
Supplier-facing messages must always be approved before dispatch.
Customer-facing messages require approval when they include commercial commitments.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

_DATA_DIR = Path("data/message_drafts")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MessageDraft(BaseModel):
    id: str = Field(default_factory=lambda: f"draft_{uuid.uuid4().hex[:8]}")
    project_id: str
    b_workspace_id: Optional[str] = None
    procurement_edge_id: Optional[str] = None
    channel: str
    target_peer_id: Optional[str] = None
    target_role: str  # customer / supplier / manufacturer / logistics / qc
    draft_text: str
    approval_status: str = "pending_approval"  # pending_approval / approved / rejected / edited
    approved_by_sender_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _draft_path(draft_id: str) -> Path:
    return _DATA_DIR / f"{draft_id}.json"


def _load_all() -> list[MessageDraft]:
    _ensure_dir()
    drafts = []
    for path in _DATA_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                drafts.append(MessageDraft.model_validate(json.load(f)))
        except Exception:
            pass
    return drafts


def create_draft(
    project_id: str,
    channel: str,
    target_role: str,
    draft_text: str,
    b_workspace_id: Optional[str] = None,
    procurement_edge_id: Optional[str] = None,
    target_peer_id: Optional[str] = None,
) -> MessageDraft:
    _ensure_dir()
    draft = MessageDraft(
        project_id=project_id,
        b_workspace_id=b_workspace_id,
        procurement_edge_id=procurement_edge_id,
        channel=channel,
        target_peer_id=target_peer_id,
        target_role=target_role,
        draft_text=draft_text,
    )
    _save(draft)
    return draft


def find_pending_drafts(project_id: str) -> list[MessageDraft]:
    return [
        d for d in _load_all()
        if d.project_id == project_id and d.approval_status == "pending_approval"
    ]


def find_draft_by_id(draft_id: str) -> Optional[MessageDraft]:
    path = _draft_path(draft_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return MessageDraft.model_validate(json.load(f))


def approve_draft(draft_id: str, approved_by_sender_id: str) -> Optional[MessageDraft]:
    draft = find_draft_by_id(draft_id)
    if draft is None:
        return None
    draft.approval_status = "approved"
    draft.approved_by_sender_id = approved_by_sender_id
    draft.approved_at = _utcnow()
    draft.updated_at = _utcnow()
    _save(draft)
    return draft


def reject_draft(draft_id: str) -> Optional[MessageDraft]:
    draft = find_draft_by_id(draft_id)
    if draft is None:
        return None
    draft.approval_status = "rejected"
    draft.updated_at = _utcnow()
    _save(draft)
    return draft


def _save(draft: MessageDraft) -> None:
    _ensure_dir()
    path = _draft_path(draft.id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(draft.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
