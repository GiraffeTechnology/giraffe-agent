"""B-side buyer sign-off after delivery."""
from src.m_side.m_event_logger import log_m_event


def request_buyer_signoff(project_id: str, buyer_actor_id: str, tracking_number: str) -> dict:
    msg = (
        f"The shipment ({tracking_number}) has been marked as delivered. "
        "Please confirm receipt:\n"
        "A. Confirm received\n"
        "B. Not received\n"
        "C. Received with issue"
    )
    log_m_event(
        event_type="BUYER_SIGNOFF_REQUESTED",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={"tracking_number": tracking_number, "message": msg},
    )
    return {"status": "signoff_requested", "message": msg}


def receive_buyer_signoff(
    project_id: str,
    buyer_actor_id: str,
    response: str = "confirmed",
    notes: str = "",
    order_id: str | None = None,
    tracking_number: str | None = None,
) -> dict:
    log_m_event(
        event_type="BUYER_SIGNOFF_RECEIVED",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={
            "response": response,
            "notes": notes,
            "order_id": order_id,
            "tracking_number": tracking_number,
        },
    )

    order_status_updated = False

    if response == "confirmed":
        # Update order execution status to ORDER_CLOSED
        _order_id = order_id
        if not _order_id:
            try:
                from src.merchandiser.merchandiser_engine import find_execution_plan_by_project_id
                plan = find_execution_plan_by_project_id(project_id)
                if plan:
                    _order_id = plan.order_id
            except Exception:
                pass

        if _order_id:
            try:
                from src.m_side.order_acknowledger import get_order_execution, save_order_execution
                order_ctx = get_order_execution(_order_id)
                if order_ctx and order_ctx.status not in ("ORDER_CLOSED", "CANCELLED"):
                    order_ctx.status = "ORDER_CLOSED"
                    save_order_execution(order_ctx)
                    order_status_updated = True
                    log_m_event(
                        event_type="ORDER_CLOSED_AFTER_BUYER_SIGNOFF",
                        b_workspace_id=project_id,
                        supplier_id=buyer_actor_id,
                        payload={
                            "order_id": _order_id,
                            "tracking_number": tracking_number,
                            "buyer_response": response,
                        },
                    )
            except Exception:
                pass

        # Also update merchandiser execution plan state
        try:
            from src.merchandiser.merchandiser_state_machine import transition_order_state
            transition_order_state(
                project_id=project_id,
                to_state="BUYER_SIGNED_OFF",
                reason=f"Buyer confirmed receipt. Notes: {notes[:200]}" if notes else "Buyer confirmed receipt.",
                buyer_actor_id=buyer_actor_id,
            )
        except Exception:
            pass

    return {
        "status": "order_closed" if response == "confirmed" else "signoff_received",
        "response": response,
        "order_id": order_id,
        "order_status_updated": order_status_updated,
    }
