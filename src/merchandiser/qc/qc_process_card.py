"""
QC process card — supplier process card storage with LLM-safe redaction.
Persisted under data/merchandiser/qc/process_cards/.

Security: By default, pricing / contact info is redacted before sending to LLM.
Control via QC_ALLOW_EXTERNAL_LLM (default: false), QC_ALLOW_CAD_TO_LLM (default: false).
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field
from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/merchandiser/qc/process_cards")

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

class QCProcessCard(BaseModel):
    process_card_id: str
    project_id: str
    category: str
    material_spec: str | None = None
    color_spec: str | None = None
    size_spec: str | None = None
    finish_spec: str | None = None
    defect_criteria: str | None = None
    supplier_notes: str | None = None
    # Sensitive fields — not sent to LLM by default
    unit_price: float | None = None
    supplier_contact: str | None = None
    contract_terms: str | None = None
    is_active: bool = True
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)

def create_process_card(
    project_id: str,
    category: str,
    material_spec: str | None = None,
    color_spec: str | None = None,
    size_spec: str | None = None,
    finish_spec: str | None = None,
    defect_criteria: str | None = None,
    supplier_notes: str | None = None,
    unit_price: float | None = None,
    supplier_contact: str | None = None,
    contract_terms: str | None = None,
) -> QCProcessCard:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    card = QCProcessCard(
        process_card_id=f"PC-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        category=category,
        material_spec=material_spec,
        color_spec=color_spec,
        size_spec=size_spec,
        finish_spec=finish_spec,
        defect_criteria=defect_criteria,
        supplier_notes=supplier_notes,
        unit_price=unit_price,
        supplier_contact=supplier_contact,
        contract_terms=contract_terms,
    )
    _save_card(card)
    log_m_event(
        event_type="QC_PROCESS_CARD_CREATED",
        b_workspace_id=project_id,
        payload={"process_card_id": card.process_card_id, "category": category},
    )
    return card

def _save_card(card: QCProcessCard) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    card.updated_at = _utcnow()
    (_DATA_DIR / f"{card.process_card_id}.json").write_text(card.model_dump_json(indent=2), encoding="utf-8")

def get_process_card(project_id: str) -> QCProcessCard | None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    cards = []
    for p in _DATA_DIR.glob("PC-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            card = QCProcessCard.model_validate(data)
            if card.project_id == project_id and card.is_active:
                cards.append(card)
        except Exception:
            pass
    if not cards:
        return None
    return max(cards, key=lambda c: c.created_at)
    return None

def render_process_card_for_llm(card: QCProcessCard) -> str:
    """Render process card as a text string safe to send to LLM (sensitive fields redacted by default)."""
    allow_external = os.getenv("QC_ALLOW_EXTERNAL_LLM", "false").lower() == "true"
    allow_cad = os.getenv("QC_ALLOW_CAD_TO_LLM", "false").lower() == "true"
    allow_bom = os.getenv("QC_ALLOW_BOM_TO_LLM", "false").lower() == "true"

    parts = [f"工艺卡 / Process Card (Project: {card.project_id}, Category: {card.category})"]
    if card.material_spec:
        if allow_cad or allow_external:
            parts.append(f"材料规格 / Material: {card.material_spec}")
        else:
            parts.append("材料规格 / Material: [redacted — set QC_ALLOW_CAD_TO_LLM=true to include]")
    if card.color_spec:
        parts.append(f"颜色 / Color: {card.color_spec}")
    if card.size_spec:
        if allow_bom or allow_external:
            parts.append(f"尺寸 / Size: {card.size_spec}")
        else:
            parts.append("尺寸 / Size: [redacted — set QC_ALLOW_BOM_TO_LLM=true to include]")
    if card.finish_spec:
        parts.append(f"表面处理 / Finish: {card.finish_spec}")
    if card.defect_criteria:
        parts.append(f"缺陷标准 / Defect criteria: {card.defect_criteria}")
    if card.supplier_notes:
        parts.append(f"工厂备注 / Supplier notes: {card.supplier_notes}")
    # Never include pricing, contact, or contract terms in LLM calls
    return "\n".join(parts)

def redact_process_card_for_llm(card: QCProcessCard) -> dict:
    """Return a redacted dict representation (never includes pricing/contact/contract)."""
    return {
        "process_card_id": card.process_card_id,
        "project_id": card.project_id,
        "category": card.category,
        "color_spec": card.color_spec,
        "finish_spec": card.finish_spec,
        "defect_criteria": card.defect_criteria,
        "supplier_notes": card.supplier_notes,
        # material_spec, size_spec gated by env vars
        "material_spec": card.material_spec if os.getenv("QC_ALLOW_CAD_TO_LLM", "false").lower() == "true" else None,
        "size_spec": card.size_spec if os.getenv("QC_ALLOW_BOM_TO_LLM", "false").lower() == "true" else None,
    }
