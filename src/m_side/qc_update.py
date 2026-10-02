# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
"""
M-side QC update handler.
"""

from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone

from src.core_schema.m_side_types import QCUpdate, OrderExecutionContext
from src.m_side.order_acknowledger import get_order_execution, save_order_execution
from src.m_side.m_event_logger import log_m_event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def submit_qc_update(
    order_execution_id: str,
    supplier_id: str,
    message: str,
    attachments: list[dict] | None = None,
) -> QCUpdate:
    """
    Create a QC update from supplier message and attachment metadata.
    For MVP, attachment content is stored as metadata — no computer vision required.
    """
    # Detect QC status from message
    qc_status = "pending"
    if re.search('\u5408\u683c|passed|pass|ok|\u901a\u8fc7|approved', message, re.IGNORECASE):
        qc_status = "passed"
    elif re.search('\u4e0d\u5408\u683c|failed|fail|reject|\u62d2\u7edd|\u4e0d\u901a\u8fc7', message, re.IGNORECASE):
        qc_status = "failed"
    elif re.search('\u9700\u8981\u786e\u8ba4|\u9700\u4e70\u5bb6\u786e\u8ba4|buyer.*confirm|needs.*confirmation', message, re.IGNORECASE):
        qc_status = "needs_buyer_confirmation"

    qc_update = QCUpdate(
        qc_update_id=f"QC-{uuid.uuid4().hex[:8].upper()}",
        order_execution_id=order_execution_id,
        supplier_id=supplier_id,
        qc_status=qc_status,
        message=message,
        attachments=attachments or [],
        created_at=_utcnow(),
    )

    # Update order execution QC milestone
    try:
        order = get_order_execution(order_execution_id)
        for milestone in order.milestones:
            if milestone.name == "qc_confirmation":
                milestone.status = "completed" if qc_status == "passed" else "in_progress"
                milestone.notes = message[:100]
                break

        if qc_status == "passed" and order.status == "in_production":
            order.status = "qc_pending"

        save_order_execution(order)
    except FileNotFoundError:
        pass

    log_m_event(
        event_type="M_QC_UPDATE_RECEIVED",
        order_execution_id=order_execution_id,
        supplier_id=supplier_id,
        payload={
            "qc_status": qc_status,
            "message": message[:200],
            "attachments": attachments or [],
        },
    )

    return qc_update
