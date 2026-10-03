"""Build canonical-English QC comparison prompts without changing the report schema."""

from __future__ import annotations
_QC_SYSTEM_PROMPT = (
    "You are the Giraffe Agent QC assistant. Compare:\n"
    "1. Production images or video frames uploaded by the manufacturer;\n"
    "2. Approved reference images or golden samples;\n"
    "3. The process card;\n"
    "4. The order requirements.\n"
    "Assess consistency with the approved standard and return strict JSON.\n"
    "Requirements:\n"
    "- Do not invent measurements that cannot be established from images.\n"
    "- Request close-up images when evidence is unclear.\n"
    "- Do not provide final legal acceptance.\n"
    "- Provide actionable rework, evidence and reinspection guidance.\n"
    "- Request buyer review for serious issues.\n"
    "- Use English for all business feedback and summaries.\n"
    "- Populate m_side_feedback_en; retain the legacy m_side_feedback_zh field as empty.\n"
    "  Requested localization is rendered separately by giraffe-language-skill.\n"
)

_QC_JSON_SCHEMA = """\
{
  "overall_result": "pass | needs_fix | buyer_review_required | reject | unknown",
  "overall_score": 0.0,
  "severity": "low | medium | high | critical | unknown",
  "detected_deviations": [
    {"field": "", "expected": "", "actual": "", "severity": "low|medium|high|critical", "note": ""}
  ],
  "process_card_violations": [],
  "buyer_confirmation_required": false,
  "human_review_required": false,
  "m_side_feedback_zh": "",
  "m_side_feedback_en": "",
  "b_side_summary": ""
}\
"""


def build_qc_system_prompt() -> str:
    return _QC_SYSTEM_PROMPT


def build_qc_user_prompt(
    milestone_type: str | None = None,
    order_requirements: str | None = None,
    process_card_notes: str | None = None,
    standard_image_count: int = 0,
    production_image_count: int = 0,
) -> str:
    parts = []
    if milestone_type:
        parts.append(f"Milestone: {milestone_type}")
    if order_requirements:
        parts.append(f"Order requirements:\n{order_requirements}")
    if process_card_notes:
        parts.append(f"Process card:\n{process_card_notes}")
    parts.append(
        f"Image order: the first {standard_image_count} images are approved reference images; "
        f"the following {production_image_count} images show actual production."
    )
    parts.append(f"\nReturn only JSON matching the following schema, without Markdown fences:\n{_QC_JSON_SCHEMA}")
    return "\n\n".join(parts)
