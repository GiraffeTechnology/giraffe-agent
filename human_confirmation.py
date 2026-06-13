"""Human confirmation gate for the B/M-side trust boundary.

Manages the lifecycle of human-in-the-loop confirmation events:

  HUMAN_CONFIRMATION_REQUIRED  — AI requests human sign-off
  HUMAN_CONFIRMATION_RECEIVED  — human provides values
  HUMAN_OVERRIDE_DETECTED      — human-confirmed value differs from supplier-stated

Rules (per order_confirmation rule packet v1.0):
  - Order confirmation requires human sign-off on all five fields:
    selected_supplier_actor_id, confirmed_price, confirmed_currency,
    confirmed_lead_time_days, confirmed_quantity
  - AI may not autonomously confirm an order
  - Confirmed values must match supplier_response row (or HUMAN_OVERRIDE_DETECTED fires)
  - Edge status must be set to APPROVED only after confirmation

All ``src.db.*`` imports are lazy (inside functions only).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIRMATION_FIELDS: tuple = (
    "selected_supplier_actor_id",
    "confirmed_price",
    "confirmed_currency",
    "confirmed_lead_time_days",
    "confirmed_quantity",
)

# Fields that are compared to supplier-stated values for override detection.
_OVERRIDE_CHECK_MAP: Dict[str, str] = {
    "confirmed_price":         "price",
    "confirmed_currency":      "currency",
    "confirmed_lead_time_days": "lead_time_days",
    "confirmed_quantity":      "quantity",
}

EVENT_REQUIRED  = "HUMAN_CONFIRMATION_REQUIRED"
EVENT_RECEIVED  = "HUMAN_CONFIRMATION_RECEIVED"
EVENT_OVERRIDE  = "HUMAN_OVERRIDE_DETECTED"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class ConfirmationResult:
    """Outcome of recording a human confirmation."""

    def __init__(
        self,
        is_confirmed: bool,
        missing_fields: List[str],
        overrides: List[dict],
        events_written: List[str],
        edge_approved: bool,
    ) -> None:
        self.is_confirmed = is_confirmed
        self.missing_fields = missing_fields
        self.overrides = overrides
        self.events_written = events_written
        self.edge_approved = edge_approved

    def to_dict(self) -> dict:
        return {
            "is_confirmed": self.is_confirmed,
            "missing_fields": self.missing_fields,
            "overrides": self.overrides,
            "events_written": self.events_written,
            "edge_approved": self.edge_approved,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _detect_overrides(
    confirmed: Dict[str, Any],
    supplier_response: Dict[str, Any],
) -> List[dict]:
    """Compare confirmed values to supplier-stated values.

    Returns a list of override records for any field where the human-confirmed
    value differs from what the supplier stated.
    """
    overrides: List[dict] = []
    for confirmed_field, supplier_field in _OVERRIDE_CHECK_MAP.items():
        confirmed_val = confirmed.get(confirmed_field)
        supplier_val = supplier_response.get(supplier_field)
        if supplier_val is None:
            # Cannot compare — supplier did not state this value.
            continue
        if confirmed_val is not None and confirmed_val != supplier_val:
            overrides.append({
                "field": confirmed_field,
                "supplier_stated": supplier_val,
                "human_confirmed": confirmed_val,
                "note": (
                    f"Human confirmed {confirmed_field}={confirmed_val!r} but "
                    f"supplier stated {supplier_field}={supplier_val!r}. "
                    "HUMAN_OVERRIDE_DETECTED event recorded."
                ),
            })
    return overrides


def _write_event(
    adapter: Any,
    event_type: str,
    project_id: str,
    edge_id: Optional[str],
    actor_id: str,
    payload: dict,
) -> Optional[str]:
    """Write a single execution event.  Returns event_id or None on failure."""
    if adapter is None:
        return None
    try:
        event = adapter.log_event(
            event_type=event_type,
            project_id=project_id,
            actor_id=actor_id,
            edge_id=edge_id,
            payload_json=payload,
        )
        if isinstance(event, dict):
            return event.get("event_id")
        return str(uuid.uuid4())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def request_confirmation(
    project_id: str,
    edge_id: Optional[str],
    actor_id: str,
    response_summary: Dict[str, Any],
    adapter: Any = None,
) -> Optional[str]:
    """Write a HUMAN_CONFIRMATION_REQUIRED event.

    Parameters
    ----------
    project_id, edge_id, actor_id:
        Context for event logging.
    response_summary:
        Dict summarising the supplier response that requires confirmation
        (response_id, price, currency, lead_time_days, moq, etc.).
    adapter:
        Optional ``BMDbAdapter`` instance for DB persistence.

    Returns the event_id (str) or None if no adapter.
    """
    payload: Dict[str, Any] = {
        "confirmation_fields_required": list(CONFIRMATION_FIELDS),
        "response_summary": response_summary,
        "human_confirmation_required": True,
        "requested_at": _now_iso(),
        "note": (
            "AI may not autonomously confirm this order. "
            "Human must provide all five confirmation fields."
        ),
    }
    return _write_event(
        adapter, EVENT_REQUIRED, project_id, edge_id, actor_id, payload
    )


def record_confirmation(
    project_id: str,
    edge_id: Optional[str],
    confirming_actor_id: str,
    confirmed: Dict[str, Any],
    supplier_response: Dict[str, Any],
    adapter: Any = None,
) -> ConfirmationResult:
    """Record a human-provided confirmation and detect overrides.

    Parameters
    ----------
    project_id, edge_id, confirming_actor_id:
        Context for event logging.
    confirmed:
        Dict with the five confirmation fields the human has provided.
        Must contain all of: selected_supplier_actor_id, confirmed_price,
        confirmed_currency, confirmed_lead_time_days, confirmed_quantity.
    supplier_response:
        The original supplier response dict (used for override detection).
    adapter:
        Optional ``BMDbAdapter`` instance.  When supplied:
        - writes HUMAN_CONFIRMATION_RECEIVED event
        - writes HUMAN_OVERRIDE_DETECTED event for each override found
        - sets edge.status = "APPROVED" when all fields present and no
          critical fields are missing

    Returns a ``ConfirmationResult`` describing what happened.
    """
    events_written: List[str] = []

    # 1. Check for missing confirmation fields.
    missing = [f for f in CONFIRMATION_FIELDS if confirmed.get(f) is None]

    # 2. Detect overrides.
    overrides = _detect_overrides(confirmed, supplier_response)

    # 3. Write HUMAN_CONFIRMATION_RECEIVED.
    payload_received: Dict[str, Any] = {
        "confirmed": confirmed,
        "missing_confirmation_fields": missing,
        "overrides_detected": len(overrides),
        "response_id": supplier_response.get("response_id"),
        "confirmed_at": _now_iso(),
    }
    eid = _write_event(
        adapter, EVENT_RECEIVED, project_id, edge_id,
        confirming_actor_id, payload_received,
    )
    if eid:
        events_written.append(eid)

    # 4. Write HUMAN_OVERRIDE_DETECTED for each override.
    for override in overrides:
        payload_override: Dict[str, Any] = {
            "field": override["field"],
            "supplier_stated": override["supplier_stated"],
            "human_confirmed": override["human_confirmed"],
            "response_id": supplier_response.get("response_id"),
            "confirmed_at": _now_iso(),
        }
        eid_ov = _write_event(
            adapter, EVENT_OVERRIDE, project_id, edge_id,
            confirming_actor_id, payload_override,
        )
        if eid_ov:
            events_written.append(eid_ov)

    # 5. Approve the edge when all fields are provided.
    is_confirmed = len(missing) == 0
    edge_approved = False
    if is_confirmed and adapter is not None and edge_id is not None:
        try:
            adapter.update_edge(edge_id, status="APPROVED")
            edge_approved = True
        except Exception:
            pass

    return ConfirmationResult(
        is_confirmed=is_confirmed,
        missing_fields=missing,
        overrides=overrides,
        events_written=events_written,
        edge_approved=edge_approved,
    )


def assert_confirmation_required(packet: dict) -> None:
    """Raise ValueError if *packet* does not require human confirmation.

    Every buyer-facing packet must set ``human_confirmation_required=True``
    (per decision_packet_generation rule packet v1.0).
    """
    if not packet.get("human_confirmation_required"):
        raise ValueError(
            "human_confirmation_required must be True for every buyer-facing "
            f"packet. Got: {packet.get('human_confirmation_required')!r}"
        )
