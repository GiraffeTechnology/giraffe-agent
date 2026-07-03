"""
M-side supplier clarification — generates one-question-at-a-time prompts for missing fields.
"""

from __future__ import annotations
from src.core_schema.m_side_types import MSideWorkspace

_CLARIFICATION_QUESTIONS_ZH = {
    "can_make": "您好！请问贵司是否可以生产此产品？（是/否）",
    "earliest_start": "请问最早什么时候可以开工？",
    "lead_time": "请问预计总交期是多少天？",
    "material_available": "所需材料是否有现货？（有/无）",
    "unit_price": "请问单价是多少？（请注明货币）",
    "moq": "请问最低订购量（MOQ）是多少？",
    "qc_available": "贵司是否可以提供质检报告或图片/视频更新？",
    "logistics_terms": "贵司支持哪种交货条款？（EXW / FOB / DDP / 快递）",
    "risk_flags": "是否有需要提前说明的风险或限制？（如外协、材料短缺等）",
}

_CLARIFICATION_QUESTIONS_EN = {
    "can_make": "Can your company produce this item? (Yes / No)",
    "earliest_start": "What is your earliest possible start date?",
    "lead_time": "What is the estimated total lead time in days?",
    "material_available": "Is the required material available in stock? (Yes / No)",
    "unit_price": "What is the unit price? (Please specify currency)",
    "moq": "What is the minimum order quantity (MOQ)?",
    "qc_available": "Can you provide QC reports or photo/video updates?",
    "logistics_terms": "What delivery terms can you support? (EXW / FOB / DDP / courier)",
    "risk_flags": "Are there any key risks or constraints to flag? (e.g. outsourcing, material shortage)",
}


def _detect_missing_fields(workspace: MSideWorkspace) -> list[str]:
    """Determine which required fields are still missing from the workspace."""
    missing = []
    pkt = workspace.response_packet

    if pkt is None:
        # No response at all — all fields missing
        return list(_CLARIFICATION_QUESTIONS_ZH.keys())

    if pkt.capacity_signal.can_make is None:
        missing.append("can_make")
    if pkt.schedule_signal.estimated_lead_time_days is None:
        missing.append("lead_time")
    if pkt.capacity_signal.earliest_start_date is None:
        missing.append("earliest_start")
    if pkt.material_availability.material_available is None:
        missing.append("material_available")
    if pkt.quote.unit_price is None:
        missing.append("unit_price")
    if not pkt.quote.quote_notes and pkt.quote.unit_price is None:
        if "moq" not in missing:
            missing.append("moq")
    if pkt.qc_commitment.qc_available is None:
        missing.append("qc_available")
    if (
        pkt.logistics_commitment.exw_supported is None
        and pkt.logistics_commitment.fob_supported is None
        and pkt.logistics_commitment.ddp_supported is None
    ):
        missing.append("logistics_terms")

    return missing


def generate_supplier_questions(workspace: MSideWorkspace) -> list[dict]:
    """
    Generate a list of pending clarification questions for missing supplier fields.
    Uses supplier's language preference (zh by default).
    """
    missing = _detect_missing_fields(workspace)
    lang = "zh"  # Default; could check supplier profile

    questions_map = _CLARIFICATION_QUESTIONS_ZH if lang == "zh" else _CLARIFICATION_QUESTIONS_EN

    questions = []
    for field in missing:
        q = questions_map.get(field)
        if q:
            questions.append({"field": field, "question": q, "lang": lang})

    return questions


def next_supplier_question(workspace: MSideWorkspace) -> str | None:
    """
    Return the next missing supplier-side question as a formatted string.
    Returns None if all required fields are present.
    """
    questions = generate_supplier_questions(workspace)
    if not questions:
        return None
    return questions[0]["question"]
