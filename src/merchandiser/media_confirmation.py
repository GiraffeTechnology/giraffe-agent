"""
Media evidence — links uploaded media to milestones for buyer review.
Persisted under data/merchandiser/media/.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/merchandiser/media")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class MediaEvidence(BaseModel):
    media_id: str
    project_id: str
    milestone_id: str
    uploaded_by_actor_id: str
    artifact_id: str | None = None
    media_type: Literal["image", "video", "document", "shipping_label"]
    description: str | None = None
    visibility_check_status: Literal["pass", "fail", "unknown"] = "pass"
    completeness_check_status: Literal["pass", "fail", "unknown"] = "pass"
    buyer_review_status: Literal["pending", "confirmed", "rejected", "not_required"] = "pending"
    notes: str | None = None
    created_at: str = Field(default_factory=_utcnow)


def upload_media_evidence(
    project_id: str,
    milestone_id: str,
    uploaded_by_actor_id: str,
    media_type: str = "image",
    description: str | None = None,
    artifact_id: str | None = None,
    count: int = 1,
    update_milestone_status: bool = True,
) -> list[MediaEvidence]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    evidences = []
    for i in range(count):
        ev = MediaEvidence(
            media_id=f"MEDIA-{uuid.uuid4().hex[:10].upper()}",
            project_id=project_id,
            milestone_id=milestone_id,
            uploaded_by_actor_id=uploaded_by_actor_id,
            artifact_id=artifact_id,
            media_type=media_type,  # type: ignore[arg-type]
            description=description or f"Media upload {i+1}/{count}",
            buyer_review_status="pending" if media_type != "shipping_label" else "not_required",
        )
        path = _DATA_DIR / f"{ev.media_id}.json"
        path.write_text(ev.model_dump_json(indent=2), encoding="utf-8")
        evidences.append(ev)

    media_ids = [ev.media_id for ev in evidences]

    if update_milestone_status:
        try:
            from src.merchandiser.milestone_manager import update_milestone_status as _update_ms
            _update_ms(
                milestone_id=milestone_id,
                project_id=project_id,
                status="UPLOADED",
                metadata={"media_ids": media_ids, "uploaded_by": uploaded_by_actor_id},
            )
        except FileNotFoundError:
            pass

    log_m_event(
        event_type="MEDIA_EVIDENCE_UPLOADED",
        b_workspace_id=project_id,
        payload={
            "milestone_id": milestone_id,
            "uploaded_by": uploaded_by_actor_id,
            "count": count,
            "media_type": media_type,
            "media_ids": media_ids,
            "milestone_status_updated": update_milestone_status,
        },
    )
    return evidences


def get_media_for_milestone(milestone_id: str) -> list[MediaEvidence]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in _DATA_DIR.glob("MEDIA-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ev = MediaEvidence.model_validate(data)
            if ev.milestone_id == milestone_id:
                result.append(ev)
        except Exception:
            pass
    return result


def check_media_completeness(project_id: str, milestone_id: str) -> dict:
    media = get_media_for_milestone(milestone_id)
    count = len(media)
    all_valid = all(m.completeness_check_status in ("pass", "unknown") for m in media)
    log_m_event(
        event_type="MEDIA_COMPLETENESS_CHECKED",
        b_workspace_id=project_id,
        payload={"milestone_id": milestone_id, "count": count, "all_valid": all_valid},
    )
    return {"milestone_id": milestone_id, "count": count, "complete": count > 0 and all_valid}


def mark_media_buyer_confirmed(project_id: str, milestone_id: str, buyer_actor_id: str) -> dict:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    updated = 0
    for p in _DATA_DIR.glob("MEDIA-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ev = MediaEvidence.model_validate(data)
            if ev.milestone_id == milestone_id and ev.buyer_review_status == "pending":
                ev.buyer_review_status = "confirmed"  # type: ignore[assignment]
                p.write_text(ev.model_dump_json(indent=2), encoding="utf-8")
                updated += 1
        except Exception:
            pass
    log_m_event(
        event_type="ORDER_MILESTONE_BUYER_CONFIRMED",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={"milestone_id": milestone_id, "confirmed_count": updated},
    )
    return {"milestone_id": milestone_id, "confirmed_count": updated}


def mark_media_buyer_rejected(project_id: str, milestone_id: str, buyer_actor_id: str, reason: str) -> dict:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    updated = 0
    for p in _DATA_DIR.glob("MEDIA-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ev = MediaEvidence.model_validate(data)
            if ev.milestone_id == milestone_id and ev.buyer_review_status == "pending":
                ev.buyer_review_status = "rejected"  # type: ignore[assignment]
                ev.notes = reason
                p.write_text(ev.model_dump_json(indent=2), encoding="utf-8")
                updated += 1
        except Exception:
            pass
    log_m_event(
        event_type="ORDER_MILESTONE_REJECTED",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={"milestone_id": milestone_id, "reason": reason},
    )
    return {"milestone_id": milestone_id, "rejected_count": updated, "reason": reason}
