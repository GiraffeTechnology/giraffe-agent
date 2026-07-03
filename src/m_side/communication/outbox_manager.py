"""
Outbox manager — creates and tracks outbound messages requiring approval.
Persisted under data/communication/outbox/.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/communication/outbox")

_APPROVAL_REQUIRED_PURPOSES = {
    "upstream_inquiry_to_supplier",
    "supplier_response_rollup_to_buyer",
    "exception_report",
    "logistics_handover",
}


class OutboundMessage(BaseModel):
    outbound_message_id: str
    project_id: str
    edge_id: str
    from_actor_id: str
    to_actor_id: str
    role_context_id: str
    thread_id: str
    message_purpose: str
    body: str
    channel_type: str
    status: Literal["DRAFT", "APPROVAL_REQUIRED", "READY_TO_SEND", "SENT", "FAILED"] = "DRAFT"
    requires_approval: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sent_at: str | None = None


def create_outbound_message(
    project_id: str,
    from_actor_id: str,
    to_actor_id: str,
    edge_id: str,
    role_context_id: str,
    message_purpose: str,
    body: str,
    channel_type: str = "mock",
    thread_id: str = "",
) -> OutboundMessage:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    requires_approval = message_purpose in _APPROVAL_REQUIRED_PURPOSES
    msg = OutboundMessage(
        outbound_message_id=f"OUT-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        edge_id=edge_id,
        from_actor_id=from_actor_id,
        to_actor_id=to_actor_id,
        role_context_id=role_context_id,
        thread_id=thread_id,
        message_purpose=message_purpose,
        body=body,
        channel_type=channel_type,
        status="APPROVAL_REQUIRED" if requires_approval else "READY_TO_SEND",
        requires_approval=requires_approval,
    )
    path = _DATA_DIR / f"{msg.outbound_message_id}.json"
    path.write_text(msg.model_dump_json(indent=2), encoding="utf-8")
    log_m_event(
        event_type="M_OUTBOUND_UPSTREAM_INQUIRY_CREATED",
        b_workspace_id=project_id,
        supplier_id=from_actor_id,
        payload={
            "outbound_message_id": msg.outbound_message_id,
            "to": to_actor_id,
            "purpose": message_purpose,
            "requires_approval": requires_approval,
        },
    )
    return msg


def approve_outbound_message(outbound_message_id: str) -> OutboundMessage:
    path = _DATA_DIR / f"{outbound_message_id}.json"
    msg = OutboundMessage.model_validate(json.loads(path.read_text(encoding="utf-8")))
    msg.status = "READY_TO_SEND"
    path.write_text(msg.model_dump_json(indent=2), encoding="utf-8")
    log_m_event(
        event_type="M_OUTBOUND_UPSTREAM_INQUIRY_APPROVED",
        b_workspace_id=msg.project_id,
        payload={"outbound_message_id": outbound_message_id},
    )
    return msg


def send_outbound_message(outbound_message_id: str) -> OutboundMessage:
    path = _DATA_DIR / f"{outbound_message_id}.json"
    msg = OutboundMessage.model_validate(json.loads(path.read_text(encoding="utf-8")))
    msg.status = "SENT"
    msg.sent_at = datetime.now(timezone.utc).isoformat()
    path.write_text(msg.model_dump_json(indent=2), encoding="utf-8")
    log_m_event(
        event_type="M_OUTBOUND_UPSTREAM_INQUIRY_SENT",
        b_workspace_id=msg.project_id,
        payload={"outbound_message_id": outbound_message_id, "to": msg.to_actor_id},
    )
    return msg
