"""
B+M Bridge — Notification stubs.
All notifications log to console in MVP mode; production would use real push services.
"""


from __future__ import annotations
def notify_supplier_inquiry_dispatched(
    supplier_id: str,
    m_workspace_id: str,
    token: str,
) -> None:
    """Notify (stub) that a supplier inquiry has been dispatched."""
    print(f"[Notification] Inquiry dispatched to supplier {supplier_id} "
          f"| Workspace: {m_workspace_id} | Token: {token}")


def notify_response_received(
    b_workspace_id: str,
    supplier_id: str,
    can_make: bool | None,
) -> None:
    """Notify (stub) that a supplier response has been received."""
    status = "CAN MAKE" if can_make else ("CANNOT MAKE" if can_make is False else "UNKNOWN")
    print(f"[Notification] Response received from supplier {supplier_id} "
          f"for workspace {b_workspace_id} | Status: {status}")


def notify_order_acknowledged(
    order_execution_id: str,
    supplier_id: str,
) -> None:
    """Notify (stub) that a supplier has acknowledged an order."""
    print(f"[Notification] Order acknowledged by supplier {supplier_id} "
          f"| Order: {order_execution_id}")


def notify_production_update(
    order_execution_id: str,
    supplier_id: str,
    status: str,
) -> None:
    """Notify (stub) of a production update."""
    print(f"[Notification] Production update from supplier {supplier_id} "
          f"| Order: {order_execution_id} | Status: {status}")


def notify_exception(
    order_execution_id: str | None,
    supplier_id: str,
    severity: str,
) -> None:
    """Notify (stub) of an exception report."""
    print(f"[Notification] Exception reported by supplier {supplier_id} "
          f"| Order: {order_execution_id} | Severity: {severity}")
