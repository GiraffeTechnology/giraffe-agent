"""Maps normalized logistics status to order execution state."""
from __future__ import annotations
from src.merchandiser.merchandiser_state_machine import logistics_status_to_order_state


def map_logistics_status_to_order_state(normalized_status: str) -> str | None:
    return logistics_status_to_order_state(normalized_status)
