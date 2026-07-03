"""B-side AI Merchandiser — handles buyer-facing status, milestones, and sign-off."""
from __future__ import annotations
from src.m_side.m_event_logger import log_m_event


def send_b_side_status_update(project_id: str, buyer_actor_id: str, message: str) -> dict:
    log_m_event(
        event_type="B_SIDE_STATUS_UPDATE_SENT",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={"message_preview": message[:120]},
    )
    return {"status": "sent", "message": message}


def send_logistics_update_to_buyer(
    project_id: str,
    buyer_actor_id: str,
    tracking_number: str,
    carrier_name: str | None,
    normalized_status: str,
    location: str | None = None,
    description: str | None = None,
) -> dict:
    msg = (
        f"Logistics update: Tracking {tracking_number} ({carrier_name or 'carrier unknown'}) — "
        f"status: {normalized_status}. "
        + (f"Location: {location}. " if location else "")
        + (description or "")
    )
    log_m_event(
        event_type="B_SIDE_LOGISTICS_UPDATE_SENT",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={
            "tracking_number": tracking_number,
            "normalized_status": normalized_status,
            "message": msg,
        },
    )
    return {"status": "sent", "message": msg}
