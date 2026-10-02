# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
"""
M-side order acknowledger — processes supplier order acknowledgement messages.
Persists order execution context under data/order_execution/.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.core_schema.m_side_types import OrderExecutionContext
from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/order_execution")


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _order_path(order_execution_id: str) -> Path:
    return _DATA_DIR / f"{order_execution_id}.json"


def get_order_execution(order_execution_id: str) -> OrderExecutionContext:
    """Load order execution context from disk."""
    _ensure_dir()
    path = _order_path(order_execution_id)
    if not path.exists():
        raise FileNotFoundError(f"Order execution not found: {order_execution_id}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return OrderExecutionContext.model_validate(data)


def save_order_execution(order: OrderExecutionContext) -> OrderExecutionContext:
    """Persist order execution context."""
    _ensure_dir()
    order.updated_at = _utcnow()
    path = _order_path(order.order_execution_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(order.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    return order


def acknowledge_order(order_execution_id: str, supplier_message: str) -> OrderExecutionContext:
    """
    Supplier acknowledges selected order path and moves execution status forward.
    Supports order-confirmation messages in Chinese and English.
    """
    order = get_order_execution(order_execution_id)

    # Update order_acknowledgement milestone
    for milestone in order.milestones:
        if milestone.name == "order_acknowledgement":
            milestone.status = "completed"
            milestone.notes = supplier_message[:200]
            break

    # Parse expected completion date if mentioned
    date_match = re.search(
        '(?:\u9884\u8ba1|expected|complete by|finish by)\\s*([A-Za-z0-9\u6708\u65e5\\s]+\\d+)',
        supplier_message,
        re.IGNORECASE,
    )
    if date_match:
        for milestone in order.milestones:
            if milestone.name == "completed":
                milestone.expected_date = date_match.group(1).strip()

    order.status = "order_acknowledged"

    log_m_event(
        event_type="M_ORDER_ACKNOWLEDGED",
        m_workspace_id=order.m_workspace_id,
        b_workspace_id=order.b_workspace_id,
        supplier_id=order.supplier_id,
        order_execution_id=order_execution_id,
        payload={"message": supplier_message[:200]},
    )

    return save_order_execution(order)
