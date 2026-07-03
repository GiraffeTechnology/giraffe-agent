from __future__ import annotations
from typing import Literal

OrderExecutionState = Literal[
    "ORDER_CONFIRMED",
    "SUPPLIER_ACCEPTANCE_PENDING",
    "SUPPLIER_ACCEPTED",
    "PRODUCTION_PLAN_CREATED",
    "MATERIAL_CONFIRMATION_PENDING",
    "MATERIAL_CONFIRMED",
    "PRODUCTION_STARTED",
    "MILESTONE_PENDING",
    "MILESTONE_MEDIA_REQUESTED",
    "MILESTONE_MEDIA_UPLOADED",
    "MILESTONE_BUYER_REVIEW_PENDING",
    "MILESTONE_CONFIRMED",
    "QC_PENDING",
    "QC_CONFIRMED",
    "PACKAGING_PENDING",
    "PACKAGING_CONFIRMED",
    "LOGISTICS_HANDOVER_PENDING",
    "LOGISTICS_HANDOVER_RECEIVED",
    "IN_TRANSIT",
    "CUSTOMS",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "BUYER_SIGNOFF_PENDING",
    "BUYER_SIGNED_OFF",
    "ORDER_CLOSED",
    "EXCEPTION_RAISED",
    "EXCEPTION_RESOLUTION_PENDING",
    "EXCEPTION_RESOLVED",
    "CANCELLED",
]

# Logistics status → order state mapping
_LOGISTICS_TO_ORDER: dict[str, str] = {
    "label_created": "LOGISTICS_HANDOVER_RECEIVED",
    "picked_up": "IN_TRANSIT",
    "in_transit": "IN_TRANSIT",
    "customs": "CUSTOMS",
    "out_for_delivery": "OUT_FOR_DELIVERY",
    "delivered": "DELIVERED",
    "exception": "EXCEPTION_RAISED",
}


def logistics_status_to_order_state(normalized_status: str) -> str | None:
    return _LOGISTICS_TO_ORDER.get(normalized_status)


_VALID_TRANSITIONS: dict[str, set[str]] = {
    "ORDER_CONFIRMED": {"SUPPLIER_ACCEPTANCE_PENDING", "EXCEPTION_RAISED", "CANCELLED"},
    "SUPPLIER_ACCEPTANCE_PENDING": {"SUPPLIER_ACCEPTED", "EXCEPTION_RAISED", "CANCELLED"},
    "SUPPLIER_ACCEPTED": {"PRODUCTION_PLAN_CREATED", "MATERIAL_CONFIRMATION_PENDING", "EXCEPTION_RAISED"},
    "PRODUCTION_PLAN_CREATED": {"MATERIAL_CONFIRMATION_PENDING", "PRODUCTION_STARTED"},
    "MATERIAL_CONFIRMATION_PENDING": {"MATERIAL_CONFIRMED", "EXCEPTION_RAISED"},
    "MATERIAL_CONFIRMED": {"PRODUCTION_STARTED"},
    "PRODUCTION_STARTED": {"MILESTONE_PENDING", "MILESTONE_MEDIA_REQUESTED", "QC_PENDING", "EXCEPTION_RAISED"},
    "MILESTONE_PENDING": {"MILESTONE_MEDIA_REQUESTED", "MILESTONE_CONFIRMED", "EXCEPTION_RAISED"},
    "MILESTONE_MEDIA_REQUESTED": {"MILESTONE_MEDIA_UPLOADED"},
    "MILESTONE_MEDIA_UPLOADED": {"MILESTONE_BUYER_REVIEW_PENDING"},
    "MILESTONE_BUYER_REVIEW_PENDING": {"MILESTONE_CONFIRMED", "EXCEPTION_RAISED"},
    "MILESTONE_CONFIRMED": {"MILESTONE_PENDING", "QC_PENDING", "PACKAGING_PENDING"},
    "QC_PENDING": {"QC_CONFIRMED", "EXCEPTION_RAISED"},
    "QC_CONFIRMED": {"PACKAGING_PENDING"},
    "PACKAGING_PENDING": {"PACKAGING_CONFIRMED"},
    "PACKAGING_CONFIRMED": {"LOGISTICS_HANDOVER_PENDING"},
    "LOGISTICS_HANDOVER_PENDING": {"LOGISTICS_HANDOVER_RECEIVED"},
    "LOGISTICS_HANDOVER_RECEIVED": {"IN_TRANSIT"},
    "IN_TRANSIT": {"CUSTOMS", "OUT_FOR_DELIVERY", "DELIVERED", "EXCEPTION_RAISED"},
    "CUSTOMS": {"IN_TRANSIT", "OUT_FOR_DELIVERY", "EXCEPTION_RAISED"},
    "OUT_FOR_DELIVERY": {"DELIVERED", "EXCEPTION_RAISED"},
    "DELIVERED": {"BUYER_SIGNOFF_PENDING"},
    "BUYER_SIGNOFF_PENDING": {"BUYER_SIGNED_OFF", "EXCEPTION_RAISED"},
    "BUYER_SIGNED_OFF": {"ORDER_CLOSED"},
    "ORDER_CLOSED": set(),
    "EXCEPTION_RAISED": {"EXCEPTION_RESOLUTION_PENDING", "CANCELLED"},
    "EXCEPTION_RESOLUTION_PENDING": {"EXCEPTION_RESOLVED", "CANCELLED"},
    "EXCEPTION_RESOLVED": {"PRODUCTION_STARTED", "QC_PENDING", "LOGISTICS_HANDOVER_PENDING"},
    "CANCELLED": set(),
}


def can_transition(from_state: str, to_state: str) -> bool:
    allowed = _VALID_TRANSITIONS.get(from_state, set())
    return to_state in allowed


def assert_transition_allowed(from_state: str, to_state: str) -> None:
    if not can_transition(from_state, to_state):
        allowed = _VALID_TRANSITIONS.get(from_state, set())
        raise ValueError(
            f"Invalid state transition: {from_state!r} → {to_state!r}. "
            f"Allowed: {sorted(allowed)}"
        )


def transition_order_state(
    project_id: str,
    to_state: str,
    reason: str,
    plan_id: str | None = None,
    order_id: str | None = None,
    actor_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    from src.m_side.m_event_logger import log_m_event
    log_m_event(
        event_type="ORDER_STATE_CHANGED",
        b_workspace_id=project_id,
        payload={
            "to_state": to_state,
            "reason": reason,
            "plan_id": plan_id,
            "order_id": order_id,
            "actor_id": actor_id,
            **(metadata or {}),
        },
    )
    return {"project_id": project_id, "to_state": to_state, "reason": reason}
