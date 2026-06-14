"""Pydantic models for QC comparison results."""
from typing import Literal
from pydantic import BaseModel, Field


class QCDeviation(BaseModel):
    field: str
    expected: str | None = None
    actual: str | None = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    note: str | None = None


class QCComparisonReport(BaseModel):
    overall_result: Literal["pass", "needs_fix", "buyer_review_required", "reject", "unknown"] = "unknown"
    overall_score: float = 0.0
    severity: Literal["low", "medium", "high", "critical", "unknown"] = "unknown"
    detected_deviations: list[QCDeviation] = Field(default_factory=list)
    process_card_violations: list[str] = Field(default_factory=list)
    buyer_confirmation_required: bool = False
    human_review_required: bool = False
    m_side_feedback_zh: str = ""
    m_side_feedback_en: str = ""
    b_side_summary: str = ""
    provider_name: str = "unknown"
    model_name: str = "unknown"
    requested_provider: str = "qwen"
    fallback_used: bool = False
    fallback_reason: str | None = None
    image_count: int = 0
    frames_used: int = 0
    raw_llm_text: str = ""
