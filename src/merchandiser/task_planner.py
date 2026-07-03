"""
Merchandiser task planner — creates execution tasks after order confirmation.
Persisted under data/merchandiser/tasks/.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/merchandiser/tasks")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class MerchandiserTask(BaseModel):
    task_id: str
    project_id: str
    order_id: str | None = None
    assigned_side: Literal["B_SIDE", "M_SIDE", "UPSTREAM_M_SIDE", "SYSTEM"]
    assigned_actor_id: str | None = None
    role_context_id: str | None = None
    task_type: Literal[
        "supplier_acceptance",
        "material_confirmation",
        "production_start",
        "milestone_media_upload",
        "buyer_milestone_review",
        "qc_update",
        "packaging_update",
        "logistics_handover",
        "tracking_update",
        "exception_resolution",
        "buyer_signoff",
        "supplier_memory_update",
    ]
    due_at: str | None = None
    status: Literal["PENDING", "IN_PROGRESS", "DONE", "OVERDUE", "CANCELLED"] = "PENDING"
    priority: Literal["low", "medium", "high"] = "medium"
    payload: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


def _save_task(task: MerchandiserTask) -> MerchandiserTask:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    task.updated_at = _utcnow()
    path = _DATA_DIR / f"{task.task_id}.json"
    path.write_text(task.model_dump_json(indent=2), encoding="utf-8")
    return task


def create_task(
    project_id: str,
    task_type: str,
    assigned_side: str,
    assigned_actor_id: str | None = None,
    order_id: str | None = None,
    priority: str = "medium",
    payload: dict | None = None,
    role_context_id: str | None = None,
) -> MerchandiserTask:
    task = MerchandiserTask(
        task_id=f"TASK-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        order_id=order_id,
        assigned_side=assigned_side,  # type: ignore[arg-type]
        assigned_actor_id=assigned_actor_id,
        role_context_id=role_context_id,
        task_type=task_type,  # type: ignore[arg-type]
        priority=priority,  # type: ignore[arg-type]
        payload=payload or {},
    )
    _save_task(task)
    log_m_event(
        event_type="MERCHANDISER_TASK_CREATED",
        b_workspace_id=project_id,
        payload={
            "task_id": task.task_id,
            "task_type": task_type,
            "assigned_side": assigned_side,
            "priority": priority,
        },
    )
    return task


def complete_task(task_id: str, project_id: str) -> MerchandiserTask:
    path = _DATA_DIR / f"{task_id}.json"
    task = MerchandiserTask.model_validate(json.loads(path.read_text(encoding="utf-8")))
    task.status = "DONE"
    _save_task(task)
    log_m_event(
        event_type="MERCHANDISER_TASK_COMPLETED",
        b_workspace_id=project_id,
        payload={"task_id": task_id},
    )
    return task


def get_tasks_for_project(project_id: str) -> list[MerchandiserTask]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    tasks = []
    for p in _DATA_DIR.glob("TASK-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            t = MerchandiserTask.model_validate(data)
            if t.project_id == project_id:
                tasks.append(t)
        except Exception:
            pass
    return tasks


def get_pending_task(
    project_id: str,
    task_type: str,
    assigned_actor_id: str | None = None,
) -> "MerchandiserTask | None":
    for t in get_tasks_for_project(project_id):
        if t.task_type == task_type and t.status == "PENDING":
            if assigned_actor_id is None or t.assigned_actor_id == assigned_actor_id:
                return t
    return None


def complete_task_by_type(
    project_id: str,
    task_type: str,
    assigned_actor_id: str | None = None,
    payload: dict | None = None,
) -> "MerchandiserTask | None":
    task = get_pending_task(project_id, task_type, assigned_actor_id)
    if task is None:
        return None
    if payload:
        task.payload.update(payload)
    task.status = "DONE"
    _save_task(task)
    log_m_event(
        event_type="MERCHANDISER_TASK_COMPLETED",
        b_workspace_id=project_id,
        payload={"task_id": task.task_id, "task_type": task_type},
    )
    return task


def mark_overdue_tasks(now: str | None = None) -> list["MerchandiserTask"]:
    from datetime import datetime, timezone
    threshold = now or datetime.now(timezone.utc).isoformat()
    overdue = []
    for p in _DATA_DIR.glob("TASK-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            t = MerchandiserTask.model_validate(data)
            if t.status == "PENDING" and t.due_at and t.due_at < threshold:
                t.status = "OVERDUE"
                _save_task(t)
                overdue.append(t)
        except Exception:
            pass
    return overdue


def plan_tasks_after_confirmation(
    project_id: str,
    order_id: str | None,
    supplier_actor_id: str,
    buyer_actor_id: str,
    category: str = "apparel",
) -> list[MerchandiserTask]:
    """Create the standard task set after order confirmation."""
    tasks = []

    m_tasks = [
        ("supplier_acceptance", "M_SIDE", "high"),
        ("material_confirmation", "M_SIDE", "high"),
        ("production_start", "M_SIDE", "medium"),
        ("milestone_media_upload", "M_SIDE", "medium"),
        ("qc_update", "M_SIDE", "medium"),
        ("packaging_update", "M_SIDE", "low"),
        ("logistics_handover", "M_SIDE", "high"),
    ]
    b_tasks = [
        ("buyer_milestone_review", "B_SIDE", "medium"),
        ("tracking_update", "B_SIDE", "low"),
        ("buyer_signoff", "B_SIDE", "high"),
    ]
    sys_tasks = [
        ("supplier_memory_update", "SYSTEM", "low"),
    ]

    for task_type, side, priority in m_tasks:
        tasks.append(create_task(
            project_id=project_id, task_type=task_type, assigned_side=side,
            assigned_actor_id=supplier_actor_id, order_id=order_id, priority=priority,
        ))
    for task_type, side, priority in b_tasks:
        tasks.append(create_task(
            project_id=project_id, task_type=task_type, assigned_side=side,
            assigned_actor_id=buyer_actor_id, order_id=order_id, priority=priority,
        ))
    for task_type, side, priority in sys_tasks:
        tasks.append(create_task(
            project_id=project_id, task_type=task_type, assigned_side=side,
            order_id=order_id, priority=priority,
        ))

    return tasks
