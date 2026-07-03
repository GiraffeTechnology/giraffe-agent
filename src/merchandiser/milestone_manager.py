"""
Milestone manager — creates, updates, and confirms production milestones.
Persisted under data/merchandiser/milestones/.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/merchandiser/milestones")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrderMilestone(BaseModel):
    milestone_id: str
    project_id: str
    order_id: str | None = None
    milestone_type: Literal[
        "material_arrival", "cutting", "machining", "surface_treatment",
        "assembly", "in_process_qc", "final_qc", "packaging",
        "logistics_handover", "delivery",
    ]
    sequence_no: int
    expected_at: str | None = None
    actual_at: str | None = None
    status: Literal["PENDING", "REQUESTED", "UPLOADED", "CONFIRMED", "REJECTED", "SKIPPED"] = "PENDING"
    evidence_required: bool = True
    required_media_types: list[str] = Field(default_factory=list)
    assigned_actor_id: str | None = None
    buyer_confirmation_required: bool = True
    metadata: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


_APPAREL_MILESTONES = [
    ("material_arrival", True, ["image"]),
    ("cutting", True, ["image", "image", "image"]),
    ("assembly", True, ["image"]),
    ("in_process_qc", True, ["image"]),
    ("final_qc", True, ["image", "document"]),
    ("packaging", True, ["image"]),
    ("logistics_handover", False, ["shipping_label"]),
    ("delivery", False, []),
]

_CNC_MILESTONES = [
    ("material_arrival", True, ["image"]),
    ("machining", True, ["image", "image"]),
    ("final_qc", True, ["image", "document"]),
    ("packaging", True, ["image"]),
    ("logistics_handover", False, ["shipping_label"]),
    ("delivery", False, []),
]


def _save_milestone(m: OrderMilestone) -> OrderMilestone:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    m.updated_at = _utcnow()
    path = _DATA_DIR / f"{m.milestone_id}.json"
    path.write_text(m.model_dump_json(indent=2), encoding="utf-8")
    return m


def create_milestones(
    project_id: str,
    category: str,
    assigned_actor_id: str | None = None,
    order_id: str | None = None,
) -> list[OrderMilestone]:
    plan = _CNC_MILESTONES if "cnc" in category.lower() or "machining" in category.lower() else _APPAREL_MILESTONES
    milestones = []
    for seq, (mtype, evidence_req, media_types) in enumerate(plan, start=1):
        m = OrderMilestone(
            milestone_id=f"MILE-{uuid.uuid4().hex[:10].upper()}",
            project_id=project_id,
            order_id=order_id,
            milestone_type=mtype,  # type: ignore[arg-type]
            sequence_no=seq,
            evidence_required=evidence_req,
            required_media_types=media_types,
            assigned_actor_id=assigned_actor_id,
            buyer_confirmation_required=evidence_req,
        )
        _save_milestone(m)
        log_m_event(
            event_type="ORDER_MILESTONE_CREATED",
            b_workspace_id=project_id,
            payload={"milestone_id": m.milestone_id, "milestone_type": mtype, "seq": seq},
        )
        milestones.append(m)
    return milestones


def request_milestone_media(milestone_id: str, project_id: str) -> OrderMilestone:
    m = get_milestone(milestone_id)
    m.status = "REQUESTED"
    _save_milestone(m)
    log_m_event(
        event_type="ORDER_MILESTONE_REQUESTED",
        b_workspace_id=project_id,
        payload={"milestone_id": milestone_id},
    )
    return m


def upload_milestone_evidence(milestone_id: str, project_id: str, media_ids: list[str]) -> OrderMilestone:
    m = get_milestone(milestone_id)
    m.status = "UPLOADED"
    m.actual_at = _utcnow()
    m.metadata["uploaded_media_ids"] = media_ids
    _save_milestone(m)
    log_m_event(
        event_type="ORDER_MILESTONE_MEDIA_UPLOADED",
        b_workspace_id=project_id,
        payload={"milestone_id": milestone_id, "media_count": len(media_ids)},
    )
    return m


def confirm_milestone(milestone_id: str, project_id: str) -> OrderMilestone:
    m = get_milestone(milestone_id)
    m.status = "CONFIRMED"
    _save_milestone(m)
    log_m_event(
        event_type="ORDER_MILESTONE_BUYER_CONFIRMED",
        b_workspace_id=project_id,
        payload={"milestone_id": milestone_id},
    )
    return m


def reject_milestone(milestone_id: str, project_id: str, reason: str = "") -> OrderMilestone:
    m = get_milestone(milestone_id)
    m.status = "REJECTED"
    m.metadata["rejection_reason"] = reason
    _save_milestone(m)
    log_m_event(
        event_type="ORDER_MILESTONE_REJECTED",
        b_workspace_id=project_id,
        payload={"milestone_id": milestone_id, "reason": reason},
    )
    return m


def get_milestone(milestone_id: str) -> OrderMilestone:
    path = _DATA_DIR / f"{milestone_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Milestone not found: {milestone_id}")
    return OrderMilestone.model_validate(json.loads(path.read_text(encoding="utf-8")))


def find_next_pending_milestone(project_id: str) -> "OrderMilestone | None":
    milestones = get_milestones_for_project(project_id)
    for m in milestones:
        if m.status == "PENDING":
            return m
    return None


def find_milestone_by_type(project_id: str, milestone_type: str) -> "OrderMilestone | None":
    for m in get_milestones_for_project(project_id):
        if m.milestone_type == milestone_type:
            return m
    return None


def update_milestone_status(
    milestone_id: str,
    project_id: str,
    status: str,
    actual_at: str | None = None,
    metadata: dict | None = None,
) -> "OrderMilestone":
    m = get_milestone(milestone_id)
    m.status = status  # type: ignore[assignment]
    if actual_at:
        m.actual_at = actual_at
    if metadata:
        m.metadata.update(metadata)
    _save_milestone(m)
    log_m_event(
        event_type="ORDER_MILESTONE_STATUS_UPDATED",
        b_workspace_id=project_id,
        payload={"milestone_id": milestone_id, "status": status},
    )
    return m


def get_milestones_for_project(project_id: str) -> list[OrderMilestone]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in _DATA_DIR.glob("MILE-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            m = OrderMilestone.model_validate(data)
            if m.project_id == project_id:
                result.append(m)
        except Exception:
            pass
    return sorted(result, key=lambda x: x.sequence_no)
