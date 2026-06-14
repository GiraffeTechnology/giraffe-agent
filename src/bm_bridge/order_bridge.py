"""
B+M Bridge — Order Bridge.
Creates M-side order execution workspace after B-side buyer selects a delivery path.
"""

import uuid
from datetime import datetime, timezone

from src.core_schema.m_side_types import OrderExecutionContext, ProductionMilestone
from src.b_side.workspace import get_b_workspace, save_b_workspace
from src.m_side.order_acknowledger import save_order_execution
from src.m_side.supplier_workspace import get_m_workspace, update_m_workspace_status
from src.m_side.m_event_logger import log_m_event

_DEFAULT_MILESTONES = [
    "order_acknowledgement",
    "material_confirmation",
    "production_start",
    "mid_production_update",
    "qc_confirmation",
    "packaging_ready",
    "logistics_handover",
    "shipped",
    "completed",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_order_execution_from_selected_path(
    b_workspace_id: str,
    selected_path_id: str,
) -> OrderExecutionContext:
    """
    Create M-side order execution workspace after B-side buyer selects a supplier path.

    Looks up the selected delivery path in the feasibility report to find supplier and workspace.
    Creates default production milestones.
    """
    b_workspace = get_b_workspace(b_workspace_id)

    if b_workspace.feasibility_report is None:
        raise ValueError(f"No feasibility report in workspace {b_workspace_id}")

    # Find the selected path
    selected_path = None
    for path in b_workspace.feasibility_report.paths:
        if path.path_id == selected_path_id:
            selected_path = path
            break

    if selected_path is None:
        raise ValueError(f"Path {selected_path_id} not found in feasibility report")

    supplier_id = selected_path.supplier_id

    # Find M-side workspace for this supplier+b_workspace combo
    from src.m_side.supplier_workspace import list_m_workspaces
    m_workspace_id = None
    for ws in list_m_workspaces():
        if ws.b_workspace_id == b_workspace_id and ws.supplier_id == supplier_id:
            m_workspace_id = ws.m_workspace_id
            break

    if m_workspace_id is None:
        # Create a placeholder workspace ID
        m_workspace_id = f"mw_order_{uuid.uuid4().hex[:8]}"

    # Build milestones
    milestones = [
        ProductionMilestone(
            milestone_id=f"MS-{uuid.uuid4().hex[:6].upper()}",
            name=name,
            status="pending",
            evidence_required=(name in ("qc_confirmation", "shipped", "completed")),
        )
        for name in _DEFAULT_MILESTONES
    ]

    now = _utcnow()
    order = OrderExecutionContext(
        order_execution_id=f"OE-{uuid.uuid4().hex[:10].upper()}",
        b_workspace_id=b_workspace_id,
        m_workspace_id=m_workspace_id,
        supplier_id=supplier_id,
        selected_path_id=selected_path_id,
        status="order_acknowledgement_pending",
        milestones=milestones,
        created_at=now,
        updated_at=now,
    )

    # Persist to disk
    save_order_execution(order)

    # Connect to AI Merchandiser
    try:
        from src.merchandiser.merchandiser_engine import create_post_confirmation_execution
        from src.projects.project_graph import _DATA_DIR as _PROJ_DIR
        import json as _json
        resolved_project_id = b_workspace_id
        resolved_buyer_actor_id = b_workspace_id  # fallback: workspace ID serves as buyer actor
        try:
            for _pf in _PROJ_DIR.glob("PROJ-*.json"):
                _pd = _json.loads(_pf.read_text(encoding="utf-8"))
                if _pd.get("b_workspace_id") == b_workspace_id:
                    resolved_project_id = _pd["project_id"]
                    # Use original_buyer_actor_id from project if available
                    if _pd.get("original_buyer_actor_id"):
                        resolved_buyer_actor_id = _pd["original_buyer_actor_id"]
                    break
        except Exception:
            pass
        resolved_category = "apparel"
        if b_workspace.buyer_requirement is not None:
            resolved_category = getattr(b_workspace.buyer_requirement, "category", None) or "apparel"
        plan = create_post_confirmation_execution(
            project_id=resolved_project_id,
            order_id=order.order_execution_id,
            supplier_actor_id=order.supplier_id,
            buyer_actor_id=resolved_buyer_actor_id,
            category=resolved_category,
            source="bm_order_bridge",
        )
        order.merchandiser_plan_id = plan.plan_id
        order.merchandiser_task_ids = plan.task_ids
        order.merchandiser_milestone_ids = plan.milestone_ids
        save_order_execution(order)
    except Exception as _me:
        log_m_event(
            event_type="MERCHANDISER_INTEGRATION_WARNING",
            b_workspace_id=b_workspace_id,
            payload={"warning": str(_me)[:200]},
        )

    # Update B-side workspace with selected path
    b_workspace.feasibility_report.selected_path_id = selected_path_id
    b_workspace.status = "supplier_selected"
    save_b_workspace(b_workspace)

    # Update M-side workspace status
    try:
        update_m_workspace_status(m_workspace_id, "selected_by_buyer")
    except FileNotFoundError:
        pass

    log_m_event(
        event_type="M_ORDER_EXECUTION_CREATED",
        m_workspace_id=m_workspace_id,
        b_workspace_id=b_workspace_id,
        supplier_id=supplier_id,
        rfq_id=b_workspace.rfq_id,
        order_execution_id=order.order_execution_id,
        payload={
            "selected_path_id": selected_path_id,
            "supplier_name": selected_path.supplier_name,
            "lead_time_days": selected_path.lead_time_days,
            "unit_price": selected_path.unit_price,
            "milestone_count": len(milestones),
        },
    )

    log_m_event(
        event_type="M_BUYER_SELECTED_SUPPLIER",
        m_workspace_id=m_workspace_id,
        b_workspace_id=b_workspace_id,
        supplier_id=supplier_id,
        rfq_id=b_workspace.rfq_id,
        payload={
            "selected_path_id": selected_path_id,
            "supplier_name": selected_path.supplier_name,
        },
    )

    return order
