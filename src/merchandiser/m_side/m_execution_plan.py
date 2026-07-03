"""M-side execution plan creation after order confirmation."""
from __future__ import annotations
from src.merchandiser.merchandiser_engine import create_execution_plan, ExecutionPlan


def create_m_side_execution_plan(
    project_id: str,
    supplier_actor_id: str,
    buyer_actor_id: str,
    category: str = "apparel",
    order_id: str | None = None,
) -> ExecutionPlan:
    return create_execution_plan(
        project_id=project_id,
        supplier_actor_id=supplier_actor_id,
        buyer_actor_id=buyer_actor_id,
        category=category,
        order_id=order_id,
    )
