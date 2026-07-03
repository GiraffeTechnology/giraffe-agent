"""
Inbox manager — receives and routes inbound messages.
Persisted under data/communication/inbox/.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/communication/inbox")


class InboundMessage(BaseModel):
    inbound_message_id: str
    project_id: str | None = None
    edge_id: str | None = None
    from_actor_id: str | None = None
    to_actor_id: str | None = None
    thread_id: str | None = None
    role_switch_frame_id: str | None = None
    raw_message: str
    parsed_target: str
    parsed_result_json: dict = Field(default_factory=dict)
    confidence_score: float = 0.8
    status: Literal["RECEIVED", "ROUTED", "PARSED", "NEEDS_CLARIFICATION", "FAILED"] = "RECEIVED"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def receive_inbound_message(
    raw_message: str,
    channel_context: dict,
    parsed_target: str = "unknown",
    parsed_result: dict | None = None,
    confidence_score: float = 0.8,
) -> InboundMessage:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    project_id = channel_context.get("project_id")
    msg = InboundMessage(
        inbound_message_id=f"IN-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        edge_id=channel_context.get("edge_id"),
        from_actor_id=channel_context.get("from_actor_id"),
        to_actor_id=channel_context.get("to_actor_id"),
        thread_id=channel_context.get("thread_id"),
        role_switch_frame_id=channel_context.get("role_switch_frame_id"),
        raw_message=raw_message,
        parsed_target=parsed_target,
        parsed_result_json=parsed_result or {},
        confidence_score=confidence_score,
        status="ROUTED" if parsed_target != "unknown" else "RECEIVED",
    )
    path = _DATA_DIR / f"{msg.inbound_message_id}.json"
    path.write_text(msg.model_dump_json(indent=2), encoding="utf-8")

    event_type = "M_INBOUND_BUYER_INQUIRY_ROUTED" if parsed_target == "buyer_requirement_parser" \
        else "M_INBOUND_UPSTREAM_RESPONSE_ROUTED" if parsed_target == "upstream_response_parser" \
        else "M_INBOUND_MESSAGE_RECEIVED"

    log_m_event(
        event_type=event_type,
        b_workspace_id=project_id,
        payload={
            "inbound_message_id": msg.inbound_message_id,
            "parsed_target": parsed_target,
            "confidence_score": confidence_score,
        },
    )
    return msg
