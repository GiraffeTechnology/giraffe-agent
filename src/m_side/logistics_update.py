# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
"""
M-side logistics update handler. Extracts tracking numbers and logistics status.
"""

from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone

from src.core_schema.m_side_types import LogisticsUpdate, OrderExecutionContext
from src.m_side.order_acknowledger import get_order_execution, save_order_execution
from src.m_side.m_event_logger import log_m_event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _extract_tracking_number(text: str) -> str | None:
    """Extract tracking/waybill number from text."""
    patterns = [
        '(?:\u5feb\u9012\u5355\u53f7|\u8fd0\u5355\u53f7|tracking.*?[:\uff1a]?\\s*)([A-Z]{2}\\d{8,}[A-Z]{0,2})',  # international
        r"(?:SF|JD|YT|ZT|YD|EMS)\d{10,}",  # Chinese express
        r"\b[A-Z]{2}\d{9}[A-Z]{2}\b",  # universal postal
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def _detect_carrier(text: str) -> str | None:
    """Detect carrier from tracking number prefix or keywords."""
    carriers = {
        "SF": "SF Express",
        "JD": "JD Logistics",
        "YT": "Yunda",
        "ZT": "ZTO",
        "EMS": "EMS",
        "DHL": "DHL",
        "FedEx": "FedEx",
        "UPS": "UPS",
        "TNT": "TNT",
    }
    text_upper = text.upper()
    for prefix, name in carriers.items():
        if prefix in text_upper:
            return name
    return None


def submit_logistics_update(
    order_execution_id: str,
    supplier_id: str,
    message: str,
) -> LogisticsUpdate:
    """
    Create a logistics update from supplier message.
    Extracts tracking number, carrier, and status automatically.
    """
    # Detect status
    status = "pending"
    if re.search('\u5df2\u53d1\u8d27|shipped|dispatched|\u4ea4\u4ed8\u7269\u6d41|handed over', message, re.IGNORECASE):
        status = "shipped"
    elif re.search('\u5df2\u4ea4\u4ed8|delivered|\u5230\u8fbe|arrived', message, re.IGNORECASE):
        status = "delivered"
    elif re.search('\u5907\u8d27\u5b8c\u6210|ready for pickup|packaging complete|\u53ef\u53d6\u8d27', message, re.IGNORECASE):
        status = "ready_for_pickup"
    elif re.search('\u4ea4\u4ed8\u7269\u6d41|handed.*logistics|logistics handover', message, re.IGNORECASE):
        status = "handed_over"

    tracking_number = _extract_tracking_number(message)
    carrier = _detect_carrier(message)

    logistics_update = LogisticsUpdate(
        logistics_update_id=f"LGS-{uuid.uuid4().hex[:8].upper()}",
        order_execution_id=order_execution_id,
        supplier_id=supplier_id,
        status=status,
        tracking_number=tracking_number,
        carrier=carrier,
        message=message,
        created_at=_utcnow(),
    )

    # Update order execution logistics milestone
    try:
        order = get_order_execution(order_execution_id)
        for milestone in order.milestones:
            if milestone.name == "logistics_handover" and status in ("handed_over", "shipped"):
                milestone.status = "completed"
                milestone.notes = f"Tracking: {tracking_number}" if tracking_number else message[:100]
                break
            if milestone.name == "shipped" and status == "shipped":
                milestone.status = "completed"
                break

        if status == "shipped":
            order.status = "shipped"
        elif status == "delivered":
            order.status = "buyer_signoff_pending"

        save_order_execution(order)
    except FileNotFoundError:
        pass

    log_m_event(
        event_type="M_LOGISTICS_UPDATE_RECEIVED",
        order_execution_id=order_execution_id,
        supplier_id=supplier_id,
        payload={
            "status": status,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "message": message[:200],
        },
    )

    return logistics_update
