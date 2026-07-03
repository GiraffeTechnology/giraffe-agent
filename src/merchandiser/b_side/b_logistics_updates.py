"""B-side logistics update push."""
from __future__ import annotations
from src.merchandiser.b_side.b_merchandiser_service import send_logistics_update_to_buyer


def push_logistics_update(
    project_id: str,
    buyer_actor_id: str,
    tracking_number: str,
    carrier_name: str | None,
    normalized_status: str,
    location: str | None = None,
    description: str | None = None,
) -> dict:
    return send_logistics_update_to_buyer(
        project_id=project_id,
        buyer_actor_id=buyer_actor_id,
        tracking_number=tracking_number,
        carrier_name=carrier_name,
        normalized_status=normalized_status,
        location=location,
        description=description,
    )
