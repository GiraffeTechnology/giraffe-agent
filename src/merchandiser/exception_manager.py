"""
Exception manager — raises, tracks, and resolves order exceptions.
Persisted under data/merchandiser/exceptions/.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/merchandiser/exceptions")

_HIGH_RISK_TYPES = {
    "material_shortage", "qc_issue", "quality_dispute", "price_change",
    "process_change", "lost_shipment",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrderException(BaseModel):
    exception_id: str
    project_id: str
    order_id: str | None = None
    raised_by_actor_id: str | None = None
    exception_type: Literal[
        "material_shortage", "capacity_delay", "production_delay", "qc_issue",
        "quality_dispute", "media_missing", "logistics_delay", "lost_shipment",
        "address_issue", "customs_issue", "process_change", "price_change",
        "lead_time_change", "other",
    ]
    severity: Literal["low", "medium", "high"]
    description: str
    proposed_options: list[dict] = Field(default_factory=list)
    buyer_confirmation_required: bool = False
    human_review_required: bool = False
    status: Literal["OPEN", "PENDING_CONFIRMATION", "RESOLVED", "ESCALATED", "CLOSED"] = "OPEN"
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


def raise_exception(
    project_id: str,
    exception_type: str,
    description: str,
    raised_by_actor_id: str | None = None,
    order_id: str | None = None,
    severity: str | None = None,
    proposed_options: list[dict] | None = None,
) -> OrderException:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    auto_severity = "high" if exception_type in _HIGH_RISK_TYPES else "medium"
    exc = OrderException(
        exception_id=f"EXC-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        order_id=order_id,
        raised_by_actor_id=raised_by_actor_id,
        exception_type=exception_type,  # type: ignore[arg-type]
        severity=severity or auto_severity,  # type: ignore[arg-type]
        description=description,
        proposed_options=proposed_options or [],
        buyer_confirmation_required=exception_type in _HIGH_RISK_TYPES,
        human_review_required=exception_type in {"quality_dispute", "lost_shipment"},
    )
    path = _DATA_DIR / f"{exc.exception_id}.json"
    path.write_text(exc.model_dump_json(indent=2), encoding="utf-8")
    log_m_event(
        event_type="EXCEPTION_OPTION_GENERATED",
        b_workspace_id=project_id,
        payload={
            "exception_id": exc.exception_id,
            "exception_type": exception_type,
            "severity": exc.severity,
            "buyer_confirmation_required": exc.buyer_confirmation_required,
        },
    )
    if exc.buyer_confirmation_required:
        log_m_event(
            event_type="EXCEPTION_BUYER_CONFIRMATION_REQUESTED",
            b_workspace_id=project_id,
            payload={"exception_id": exc.exception_id},
        )
    return exc


def raise_order_exception(
    project_id: str,
    exception_type: str,
    description: str,
    order_id: str | None = None,
    raised_by_actor_id: str | None = None,
    metadata: dict | None = None,
) -> OrderException:
    log_m_event(
        event_type="EXCEPTION_RAISED",
        b_workspace_id=project_id,
        payload={"exception_type": exception_type, "description": description[:200]},
    )
    return raise_exception(
        project_id=project_id,
        exception_type=exception_type,
        description=description,
        order_id=order_id,
        raised_by_actor_id=raised_by_actor_id,
    )


def generate_exception_options(exception_id: str) -> list[dict]:
    path = _DATA_DIR / f"{exception_id}.json"
    if not path.exists():
        return [
            {"option": "A", "description": "Wait and monitor"},
            {"option": "B", "description": "Escalate to human review"},
        ]
    exc = OrderException.model_validate(json.loads(path.read_text(encoding="utf-8")))
    log_m_event(
        event_type="EXCEPTION_OPTION_GENERATED",
        payload={"exception_id": exception_id, "exception_type": exc.exception_type},
    )
    return exc.proposed_options or [
        {"option": "A", "description": "Wait and monitor"},
        {"option": "B", "description": "Escalate to human review"},
    ]


def get_exceptions_for_project(project_id: str) -> list[OrderException]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in _DATA_DIR.glob("EXC-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            exc = OrderException.model_validate(data)
            if exc.project_id == project_id:
                result.append(exc)
        except Exception:
            pass
    return result


def resolve_exception(exception_id: str, project_id: str, resolution: str = "") -> OrderException:
    path = _DATA_DIR / f"{exception_id}.json"
    exc = OrderException.model_validate(json.loads(path.read_text(encoding="utf-8")))
    exc.status = "RESOLVED"
    exc.updated_at = _utcnow()
    exc.proposed_options.append({"resolution": resolution, "resolved_at": _utcnow()})
    path.write_text(exc.model_dump_json(indent=2), encoding="utf-8")
    log_m_event(
        event_type="EXCEPTION_RESOLVED",
        b_workspace_id=project_id,
        payload={"exception_id": exception_id, "resolution": resolution},
    )
    return exc
