"""
M-side response collector — appends supplier messages and builds SupplierResponsePacket.
"""

from __future__ import annotations
from src.core_schema.m_side_types import MSideWorkspace, SupplierResponsePacket
from src.m_side.supplier_workspace import get_m_workspace, save_m_workspace
from src.m_side.response_normalizer import normalize_supplier_response_text
from src.m_side.m_event_logger import log_m_event


def append_supplier_message(
    m_workspace_id: str,
    text: str,
    attachments: list[dict] | None = None,
) -> MSideWorkspace:
    """
    Append a raw supplier message to the M-side workspace and update status.
    """
    workspace = get_m_workspace(m_workspace_id)
    workspace.raw_supplier_messages.append(text)

    if workspace.status in ("inquiry_received", "supplier_identified"):
        workspace.status = "response_collecting"

    log_m_event(
        event_type="M_SUPPLIER_MESSAGE_RECEIVED",
        m_workspace_id=m_workspace_id,
        b_workspace_id=workspace.b_workspace_id,
        supplier_id=workspace.supplier_id,
        rfq_id=workspace.rfq_id,
        payload={"message_preview": text[:100], "attachments": attachments or []},
    )

    return save_m_workspace(workspace)


def build_response_packet_from_messages(m_workspace_id: str) -> SupplierResponsePacket:
    """
    Parse accumulated supplier messages and build/update SupplierResponsePacket.
    Persists the packet to the workspace.
    """
    workspace = get_m_workspace(m_workspace_id)

    if not workspace.raw_supplier_messages:
        raise ValueError(f"No supplier messages in workspace {m_workspace_id}")

    packet = normalize_supplier_response_text(
        texts=workspace.raw_supplier_messages,
        workspace=workspace,
    )

    workspace.response_packet = packet
    workspace.status = "response_draft_ready"

    log_m_event(
        event_type="M_RESPONSE_PACKET_CREATED",
        m_workspace_id=m_workspace_id,
        b_workspace_id=workspace.b_workspace_id,
        supplier_id=workspace.supplier_id,
        rfq_id=workspace.rfq_id,
        payload={
            "can_make": packet.capacity_signal.can_make,
            "lead_time_days": packet.schedule_signal.estimated_lead_time_days,
            "unit_price": packet.quote.unit_price,
            "completeness_score": packet.completeness_score,
        },
    )

    save_m_workspace(workspace)
    return packet
