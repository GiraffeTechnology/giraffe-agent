"""
M-side production update handler.
"""

from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone

from src.core_schema.m_side_types import ProductionUpdate, OrderExecutionContext
from src.m_side.order_acknowledger import get_order_execution, save_order_execution
from src.m_side.m_event_logger import log_m_event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def submit_production_update(
    order_execution_id: str,
    supplier_id: str,
    message: str,
    attachments: list[dict] | None = None,
) -> ProductionUpdate:
    """
    Create a production update from a supplier IM message.
    Automatically detects status from message content.
    """
    # Detect status from message
    status = "in_progress"
    if re.search(r"完成|finished|done|100%|completed", message, re.IGNORECASE):
        status = "completed"
    elif re.search(r"延误|delay|delayed|推迟", message, re.IGNORECASE):
        status = "delayed"
    elif re.search(r"开机|开工|started|begin|start", message, re.IGNORECASE):
        status = "in_progress"
    elif re.search(r"材料.*到|material.*arrived|备料", message, re.IGNORECASE):
        status = "in_progress"

    update = ProductionUpdate(
        update_id=f"PU-{uuid.uuid4().hex[:8].upper()}",
        order_execution_id=order_execution_id,
        supplier_id=supplier_id,
        status=status,
        message=message,
        attachments=attachments or [],
        created_at=_utcnow(),
    )

    # Persist to order execution
    try:
        order = get_order_execution(order_execution_id)
        if not hasattr(order, "production_updates"):
            pass  # OrderExecutionContext doesn't have this — we'll log only

        # Update relevant milestone
        _update_milestone_status(order, message)

        if order.status == "order_acknowledged":
            order.status = "in_production"

        save_order_execution(order)
    except FileNotFoundError:
        pass

    log_m_event(
        event_type="M_PRODUCTION_UPDATE_RECEIVED",
        order_execution_id=order_execution_id,
        supplier_id=supplier_id,
        payload={"status": status, "message": message[:200]},
    )

    return update


def _update_milestone_status(order: OrderExecutionContext, message: str) -> None:
    """Infer and update relevant milestones from message text."""
    msg_lower = message.lower()

    milestone_hints = {
        "material_confirmation": ["材料.*到", "material.*arrived", "备料完成"],
        "production_start": ["开工", "开机", "started production", "begin production"],
        "mid_production_update": [r"\d+%", "progress", "进度"],
        "qc_confirmation": ["qc", "质检", "inspection", "检验"],
        "packaging_ready": ["包装", "packaging", "packed"],
        "logistics_handover": ["发货", "shipped", "logistics", "快递"],
    }

    for milestone_name, patterns in milestone_hints.items():
        for pat in patterns:
            if re.search(pat, message, re.IGNORECASE):
                for milestone in order.milestones:
                    if milestone.name == milestone_name and milestone.status == "pending":
                        milestone.status = "in_progress"
                        milestone.notes = message[:100]
                break


def update_milestone_from_message(order_execution_id: str, message: str) -> OrderExecutionContext:
    """Infer milestone status from supplier message and update order execution."""
    order = get_order_execution(order_execution_id)
    _update_milestone_status(order, message)
    return save_order_execution(order)
