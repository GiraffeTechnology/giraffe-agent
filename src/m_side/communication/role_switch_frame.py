"""
RoleSwitchFrame — attaches every inbound/outbound message to its role and direction context.
Persisted as JSON under data/communication/frames/.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/communication/frames")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RoleSwitchFrame(BaseModel):
    frame_id: str
    project_id: str
    actor_id: str
    counterparty_actor_id: str | None = None
    edge_id: str | None = None
    role_context_id: str
    business_role: Literal[
        "ORIGINAL_BUYER", "MAIN_M_SIDE", "UPSTREAM_B_SIDE",
        "UPSTREAM_M_SIDE", "QC_SIDE", "LOGISTICS_SIDE", "SYSTEM", "UNKNOWN",
    ]
    communication_direction: Literal["INBOUND", "OUTBOUND", "INTERNAL"]
    message_purpose: str
    conversation_thread_id: str | None = None
    parent_frame_id: str | None = None
    created_at: str = Field(default_factory=_utcnow)


def create_role_switch_frame(
    project_id: str,
    actor_id: str,
    role_context_id: str,
    business_role: str,
    communication_direction: str,
    message_purpose: str,
    counterparty_actor_id: str | None = None,
    edge_id: str | None = None,
    conversation_thread_id: str | None = None,
    parent_frame_id: str | None = None,
) -> RoleSwitchFrame:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame = RoleSwitchFrame(
        frame_id=f"FRAME-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        actor_id=actor_id,
        counterparty_actor_id=counterparty_actor_id,
        edge_id=edge_id,
        role_context_id=role_context_id,
        business_role=business_role,  # type: ignore[arg-type]
        communication_direction=communication_direction,  # type: ignore[arg-type]
        message_purpose=message_purpose,
        conversation_thread_id=conversation_thread_id,
        parent_frame_id=parent_frame_id,
    )
    path = _DATA_DIR / f"{frame.frame_id}.json"
    path.write_text(frame.model_dump_json(indent=2), encoding="utf-8")

    log_m_event(
        event_type="M_ROLE_SWITCH_FRAME_CREATED",
        b_workspace_id=project_id,
        supplier_id=actor_id,
        payload={
            "frame_id": frame.frame_id,
            "business_role": frame.business_role,
            "direction": frame.communication_direction,
            "purpose": frame.message_purpose,
        },
    )
    return frame


def get_frames_for_project(project_id: str) -> list[RoleSwitchFrame]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for p in _DATA_DIR.glob("FRAME-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            f = RoleSwitchFrame.model_validate(data)
            if f.project_id == project_id:
                frames.append(f)
        except Exception:
            pass
    return frames
