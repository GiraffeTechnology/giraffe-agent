"""
QC reference image store — saves golden-sample / approved-sample images per project+milestone.
Persisted under data/merchandiser/qc/reference_images/.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field
from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/merchandiser/qc/reference_images")

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

class QCReferenceImage(BaseModel):
    ref_image_id: str
    project_id: str
    milestone_type: str | None = None
    image_path: str
    description: str | None = None
    uploaded_by_actor_id: str
    is_active: bool = True
    created_at: str = Field(default_factory=_utcnow)

def add_reference_image(
    project_id: str,
    image_path: str,
    uploaded_by_actor_id: str,
    milestone_type: str | None = None,
    description: str | None = None,
) -> QCReferenceImage:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    ref = QCReferenceImage(
        ref_image_id=f"REF-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        milestone_type=milestone_type,
        image_path=image_path,
        description=description,
        uploaded_by_actor_id=uploaded_by_actor_id,
    )
    (_DATA_DIR / f"{ref.ref_image_id}.json").write_text(ref.model_dump_json(indent=2), encoding="utf-8")
    log_m_event(
        event_type="QC_REFERENCE_IMAGE_ADDED",
        b_workspace_id=project_id,
        payload={"ref_image_id": ref.ref_image_id, "milestone_type": milestone_type},
    )
    return ref

def get_reference_images(project_id: str, milestone_type: str | None = None) -> list[QCReferenceImage]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in _DATA_DIR.glob("REF-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ref = QCReferenceImage.model_validate(data)
            if ref.project_id == project_id and ref.is_active:
                if milestone_type is None or ref.milestone_type == milestone_type:
                    result.append(ref)
        except Exception:
            pass
    return sorted(result, key=lambda x: x.created_at)

def deactivate_reference_image(ref_image_id: str) -> bool:
    p = _DATA_DIR / f"{ref_image_id}.json"
    if not p.exists():
        return False
    data = json.loads(p.read_text(encoding="utf-8"))
    ref = QCReferenceImage.model_validate(data)
    ref.is_active = False
    p.write_text(ref.model_dump_json(indent=2), encoding="utf-8")
    return True
