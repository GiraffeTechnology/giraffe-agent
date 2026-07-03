"""
Merchandiser engine — orchestrates post-confirmation execution for both B-side and M-side.
Persists execution state under data/merchandiser/executions/.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event
from src.merchandiser.task_planner import plan_tasks_after_confirmation, MerchandiserTask
from src.merchandiser.milestone_manager import create_milestones, OrderMilestone

_DATA_DIR = Path("data/merchandiser/executions")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionPlan(BaseModel):
    plan_id: str
    project_id: str
    order_id: str | None = None
    supplier_actor_id: str
    buyer_actor_id: str
    category: str
    current_order_state: str = "ORDER_CONFIRMED"
    task_ids: list[str] = Field(default_factory=list)
    milestone_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


def create_execution_plan(
    project_id: str,
    supplier_actor_id: str,
    buyer_actor_id: str,
    category: str = "apparel",
    order_id: str | None = None,
) -> ExecutionPlan:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    plan = ExecutionPlan(
        plan_id=f"EXECPLAN-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        order_id=order_id,
        supplier_actor_id=supplier_actor_id,
        buyer_actor_id=buyer_actor_id,
        category=category,
    )

    tasks = plan_tasks_after_confirmation(
        project_id=project_id,
        order_id=order_id,
        supplier_actor_id=supplier_actor_id,
        buyer_actor_id=buyer_actor_id,
        category=category,
    )
    plan.task_ids = [t.task_id for t in tasks]

    milestones = create_milestones(
        project_id=project_id,
        category=category,
        assigned_actor_id=supplier_actor_id,
        order_id=order_id,
    )
    plan.milestone_ids = [m.milestone_id for m in milestones]

    path = _DATA_DIR / f"{plan.plan_id}.json"
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    log_m_event(
        event_type="MERCHANDISER_EXECUTION_PLAN_CREATED",
        b_workspace_id=project_id,
        payload={
            "plan_id": plan.plan_id,
            "category": category,
            "task_count": len(tasks),
            "milestone_count": len(milestones),
        },
    )
    return plan


def update_order_state(plan_id: str, project_id: str, new_state: str, reason: str = "") -> ExecutionPlan:
    path = _DATA_DIR / f"{plan_id}.json"
    plan = ExecutionPlan.model_validate(json.loads(path.read_text(encoding="utf-8")))
    old_state = plan.current_order_state
    plan.current_order_state = new_state
    plan.updated_at = _utcnow()
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    log_m_event(
        event_type="ORDER_STATE_UPDATED_FROM_LOGISTICS",
        b_workspace_id=project_id,
        payload={"plan_id": plan_id, "from": old_state, "to": new_state, "reason": reason},
    )
    return plan


def get_execution_plan(plan_id: str) -> ExecutionPlan:
    path = _DATA_DIR / f"{plan_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"ExecutionPlan not found: {plan_id}")
    return ExecutionPlan.model_validate(json.loads(path.read_text(encoding="utf-8")))


def create_post_confirmation_execution(
    project_id: str,
    order_id: str | None,
    supplier_actor_id: str,
    buyer_actor_id: str,
    category: str = "apparel",
    source: str = "order_bridge",
) -> ExecutionPlan:
    return create_execution_plan(
        project_id=project_id,
        supplier_actor_id=supplier_actor_id,
        buyer_actor_id=buyer_actor_id,
        category=category,
        order_id=order_id,
    )


def find_execution_plan_by_order_id(order_id: str) -> "ExecutionPlan | None":
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    for p in _DATA_DIR.glob("EXECPLAN-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            plan = ExecutionPlan.model_validate(data)
            if plan.order_id == order_id:
                return plan
        except Exception:
            pass
    return None


def find_execution_plan_by_project_id(project_id: str) -> "ExecutionPlan | None":
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    for p in sorted(_DATA_DIR.glob("EXECPLAN-*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            plan = ExecutionPlan.model_validate(data)
            if plan.project_id == project_id:
                return plan
        except Exception:
            pass
    return None


def update_supplier_memory(project_id: str, supplier_actor_id: str, notes: str) -> None:
    """Record a supplier memory update after order closure."""
    mem_dir = Path("data/supplier_memory")
    mem_dir.mkdir(parents=True, exist_ok=True)
    update = {
        "update_id": f"MEMUPD-{uuid.uuid4().hex[:10].upper()}",
        "supplier_actor_id": supplier_actor_id,
        "project_id": project_id,
        "notes": notes,
        "created_at": _utcnow(),
    }
    path = mem_dir / f"{supplier_actor_id}_update_{uuid.uuid4().hex[:6]}.json"
    path.write_text(json.dumps(update, indent=2), encoding="utf-8")
    log_m_event(
        event_type="SUPPLIER_MEMORY_UPDATED_FROM_ORDER",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"update": notes},
    )
