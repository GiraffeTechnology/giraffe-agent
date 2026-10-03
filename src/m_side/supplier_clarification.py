"""
M-side supplier clarification — generates one-question-at-a-time prompts for missing fields.
"""

from __future__ import annotations
from src.core_schema.m_side_types import MSideWorkspace

_CLARIFICATION_QUESTIONS_ZH = {
    "can_make": "\u60a8\u597d！\u8bf7\u95ee\u8d35\u53f8\u662f\u5426\u53ef\u4ee5\u751f\u4ea7\u6b64\u4ea7\u54c1？（\u662f/\u5426）",
    "earliest_start": "\u8bf7\u95ee\u6700\u65e9\u4ec0\u4e48\u65f6\u5019\u53ef\u4ee5\u5f00\u5de5？",
    "lead_time": "\u8bf7\u95ee\u9884\u8ba1\u603b\u4ea4\u671f\u662f\u591a\u5c11\u5929？",
    "material_available": "\u6240\u9700\u6750\u6599\u662f\u5426\u6709\u73b0\u8d27？（\u6709/\u65e0）",
    "unit_price": "\u8bf7\u95ee\u5355\u4ef7\u662f\u591a\u5c11？（\u8bf7\u6ce8\u660e\u8d27\u5e01）",
    "moq": "\u8bf7\u95ee\u6700\u4f4e\u8ba2\u8d2d\u91cf（MOQ）\u662f\u591a\u5c11？",
    "qc_available": "\u8d35\u53f8\u662f\u5426\u53ef\u4ee5\u63d0\u4f9b\u8d28\u68c0\u62a5\u544a\u6216\u56fe\u7247/\u89c6\u9891\u66f4\u65b0？",
    "logistics_terms": "\u8d35\u53f8\u652f\u6301\u54ea\u79cd\u4ea4\u8d27\u6761\u6b3e？（EXW / FOB / DDP / \u5feb\u9012）",
    "risk_flags": "\u662f\u5426\u6709\u9700\u8981\u63d0\u524d\u8bf4\u660e\u7684\u98ce\u9669\u6216\u9650\u5236？（\u5982\u5916\u534f\u3001\u6750\u6599\u77ed\u7f3a\u7b49）",
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
        return list(_CLARIFICATION_QUESTIONS_EN.keys())

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
    Questions enter the workflow in canonical English; localization is a boundary concern.
    """
    missing = _detect_missing_fields(workspace)
    lang = "en"

    questions_map = _CLARIFICATION_QUESTIONS_EN

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
